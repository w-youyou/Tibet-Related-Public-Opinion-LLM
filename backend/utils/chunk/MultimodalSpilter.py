#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多模态文档分块器
支持文本、图片、视频等多种模态的文档分块处理

功能：
- 支持文本文件（.txt, .docx, .pdf, .md等）
- 支持图片文件（.jpg, .png, .jpeg, .gif, .bmp等）
- 支持视频文件（.mp4, .avi, .mov等）
- 支持混合模态文档（如包含图片的Word文档、PDF等）
- 输出格式化的分块结果，包含模态类型信息
"""

import os
import re
import base64
import tempfile
import zipfile
from typing import List, Dict, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    from docx import Document as DocxDocument
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

try:
    import pdfplumber
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_SUPPORT = True
except ImportError:
    PYMUPDF_SUPPORT = False

try:
    from PIL import Image
    IMAGE_SUPPORT = True
except ImportError:
    IMAGE_SUPPORT = False

# 尝试导入docx2pdf用于Word转PDF
try:
    from docx2pdf import convert as docx2pdf_convert
    DOCX2PDF_SUPPORT = True
except ImportError:
    DOCX2PDF_SUPPORT = False

# 导入优化的语义分块器
try:
    import sys
    import os
    # 尝试从项目根目录导入
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    from optimized_semantic_spilter import (
        split_text_to_chunks,
        split_pdf_to_chunks as semantic_split_pdf,
        split_docx_to_chunks as semantic_split_docx
    )
    SEMANTIC_SPLITTER_AVAILABLE = True
except ImportError:
    SEMANTIC_SPLITTER_AVAILABLE = False
    print("警告：无法导入optimized_semantic_spilter，将使用基础文本分块")


@dataclass
class MultimodalChunk:
    """多模态分块数据类"""
    id: int
    content: str  # 文本内容或图片/视频路径/URL
    modality_type: str  # 'text', 'image', 'video'
    metadata: Dict
    

class MultimodalSpilter:
    """多模态文档分块器"""
    
    # 支持的图片格式
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
    
    # 支持的视频格式
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v'}
    
    # 支持的文本格式
    TEXT_EXTENSIONS = {'.txt', '.md', '.markdown'}
    
    def __init__(self, 
                 text_chunk_size: int = 1000,
                 text_chunk_overlap: int = 200,
                 extract_images: bool = True,
                 temp_dir: Optional[str] = None,
                 use_semantic_splitter: bool = True,
                 min_chars: int = 800,
                 max_chars: int = 1800,
                 window_size: int = 6,
                 smoothing_width: int = 2,
                 chunk_size: int = 1000,
                 pdf_screenshot_pages: bool = True,
                 pdf_screenshot_dpi: int = 450,
                 docx_screenshot_pages: bool = True,
                 image_region_crops: bool = True):
        """
        初始化多模态分块器
        
        Args:
            text_chunk_size: 基础文本分块大小（字符数），当use_semantic_splitter=False时使用
            text_chunk_overlap: 文本分块重叠大小，当use_semantic_splitter=False时使用
            extract_images: 是否从文档中提取图片
            temp_dir: 临时文件目录，用于保存提取的图片
            use_semantic_splitter: 是否使用优化的语义分块器处理文本
            min_chars: 语义分块最小字符数
            max_chars: 语义分块最大字符数
            window_size: 语义分块窗口大小
            smoothing_width: 语义分块平滑宽度
            chunk_size: 语义分块处理大小
            pdf_screenshot_pages: 对于包含图片的PDF页面，是否对整个页面截图（而非提取单个图片）
            pdf_screenshot_dpi: PDF页面截图的DPI（分辨率），默认150
            docx_screenshot_pages: 对于包含图片的Word文档页面，是否对整个页面截图（需要先转换为PDF）
            image_region_crops: 在整页截图基础上，是否同时按照页面中每个图片的区域裁剪单独小图
        """
        self.text_chunk_size = text_chunk_size
        self.text_chunk_overlap = text_chunk_overlap
        self.extract_images = extract_images
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self._temp_images = []  # 存储临时图片路径，用于后续清理
        self.use_semantic_splitter = use_semantic_splitter and SEMANTIC_SPLITTER_AVAILABLE
        # 语义分块器参数
        self.min_chars = min_chars
        self.max_chars = max_chars
        self.window_size = window_size
        self.smoothing_width = smoothing_width
        self.chunk_size = chunk_size
        # PDF截图参数
        self.pdf_screenshot_pages = pdf_screenshot_pages
        self.pdf_screenshot_dpi = pdf_screenshot_dpi
        # Word截图参数
        self.docx_screenshot_pages = docx_screenshot_pages
        # 是否保留图片区域裁剪
        self.image_region_crops = image_region_crops
    
    def detect_modality(self, file_path: str) -> str:
        """检测文件模态类型"""
        ext = Path(file_path).suffix.lower()
        
        if ext in self.IMAGE_EXTENSIONS:
            return 'image'
        elif ext in self.VIDEO_EXTENSIONS:
            return 'video'
        elif ext in {'.txt', '.md', '.markdown'}:
            return 'text'
        elif ext in {'.docx', '.doc', '.pdf'}:
            return 'multimodal'  # 可能包含文本和图片
        else:
            return 'unknown'
    
    def split_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """将文本分块"""
        if chunk_size is None:
            chunk_size = self.text_chunk_size
        if overlap is None:
            overlap = self.text_chunk_overlap
        
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # 尝试在句子边界处截断
            if end < len(text):
                # 查找最后一个句号、问号、感叹号或换行符
                sentence_end = max(
                    chunk.rfind('。'),
                    chunk.rfind('！'),
                    chunk.rfind('？'),
                    chunk.rfind('.'),
                    chunk.rfind('!'),
                    chunk.rfind('?'),
                    chunk.rfind('\n')
                )
                if sentence_end > chunk_size * 0.5:  # 至少保留一半
                    chunk = chunk[:sentence_end + 1]
                    end = start + len(chunk)
            
            chunks.append(chunk.strip())
            start = end - overlap
        
        return chunks
    
    def read_text_file(self, file_path: str) -> str:
        """读取纯文本文件"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise ValueError(f"无法读取文件: {file_path}")
    
    def read_docx(self, file_path: str) -> Tuple[str, List[str]]:
        """读取DOCX文件，返回文本和图片路径列表"""
        if not DOCX_SUPPORT:
            raise ImportError("需要安装 python-docx: pip install python-docx")
        
        doc = DocxDocument(file_path)
        text_parts = []
        image_paths = []
        
        # 提取文本
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text.strip())
        
        # 提取图片（如果有）
        if self.extract_images:
            image_paths = self._extract_images_from_docx(file_path)
        
        return '\n'.join(text_parts), image_paths
    
    def read_pdf(self, file_path: str) -> Tuple[str, List[str]]:
        """读取PDF文件，返回文本和图片路径列表"""
        if not PDF_SUPPORT:
            raise ImportError("需要安装 pdfplumber 或 PyPDF2")
        
        text_parts = []
        image_paths = []
        
        try:
            # 优先使用pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
        except:
            # 备用方案：使用PyPDF2
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
        
        # 提取图片
        if self.extract_images:
            image_paths = self._extract_images_from_pdf(file_path)
        
        return '\n\n'.join(text_parts), image_paths
    
    def _extract_images_from_docx(self, file_path: str) -> List[str]:
        """
        从DOCX文件中提取图片
        
        如果启用docx_screenshot_pages，会先将Word转换为PDF，然后对包含图片的页面进行截图
        否则提取Word文档中的单个图片
        
        Args:
            file_path: DOCX文件路径
            
        Returns:
            提取的图片文件路径列表（或页面截图路径列表）
        """
        image_paths = []
        
        # 如果启用页面截图模式，先检测是否有图片，然后转换为PDF截图
        if self.docx_screenshot_pages:
            # 先检测文档是否包含图片
            has_images = False
            try:
                with zipfile.ZipFile(file_path, 'r') as docx_zip:
                    file_list = docx_zip.namelist()
                    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
                    media_files = [f for f in file_list if f.startswith('word/media/')]
                    
                    for media_file in media_files:
                        file_ext = Path(media_file).suffix.lower()
                        if file_ext in image_extensions:
                            has_images = True
                            break
            except Exception as e:
                print(f"警告：检测DOCX图片时出错: {e}")
            
            # 如果包含图片，转换为PDF然后截图
            if has_images:
                if DOCX2PDF_SUPPORT and PYMUPDF_SUPPORT:
                    try:
                        # 转换为PDF（临时文件）
                        temp_pdf_path = os.path.join(
                            self.temp_dir,
                            f"docx_to_pdf_{os.path.basename(file_path)}_{os.getpid()}.pdf"
                        )
                        
                        # 转换Word为PDF
                        docx2pdf_convert(file_path, temp_pdf_path)
                        
                        if os.path.exists(temp_pdf_path):
                            # 对PDF进行页面截图（复用PDF截图逻辑）
                            pdf_image_paths = self._extract_images_from_pdf(temp_pdf_path)
                            
                            # 重命名截图文件，标识为Word文档
                            for pdf_img_path in pdf_image_paths:
                                try:
                                    # 重命名为Word截图标识
                                    old_name = Path(pdf_img_path).name
                                    if 'pdf_page' in old_name:
                                        # 替换为docx_page（包括整页截图与裁剪小图）
                                        new_name = old_name.replace('pdf_page', 'docx_page')
                                        new_path = os.path.join(
                                            os.path.dirname(pdf_img_path),
                                            new_name
                                        )
                                        os.rename(pdf_img_path, new_path)
                                        image_paths.append(new_path)
                                        self._temp_images.append(new_path)
                                    else:
                                        image_paths.append(pdf_img_path)
                                except Exception as e:
                                    print(f"警告：重命名Word截图文件失败: {e}")
                            
                            # 清理临时PDF文件
                            try:
                                if os.path.exists(temp_pdf_path):
                                    os.remove(temp_pdf_path)
                            except:
                                pass
                        else:
                            print("警告：Word转PDF失败，PDF文件未生成")
                            # 回退到提取单个图片
                            image_paths = self._extract_images_from_docx_individual(file_path)
                    
                    except Exception as e:
                        print(f"警告：Word页面截图失败: {e}")
                        # 回退到提取单个图片
                        image_paths = self._extract_images_from_docx_individual(file_path)
                else:
                    if not DOCX2PDF_SUPPORT:
                        print("警告：需要安装 docx2pdf 才能使用Word页面截图功能（pip install docx2pdf）")
                    if not PYMUPDF_SUPPORT:
                        print("警告：需要安装 PyMuPDF 才能使用Word页面截图功能")
                    # 回退到提取单个图片
                    image_paths = self._extract_images_from_docx_individual(file_path)
            else:
                # 没有图片，不需要处理
                pass
        else:
            # 原有逻辑：提取单个图片
            image_paths = self._extract_images_from_docx_individual(file_path)
        
        return image_paths
    
    def _extract_images_from_docx_individual(self, file_path: str) -> List[str]:
        """
        从DOCX文件中提取单个图片（原有逻辑）
        
        Args:
            file_path: DOCX文件路径
            
        Returns:
            提取的图片文件路径列表
        """
        image_paths = []
        
        try:
            # DOCX文件实际上是一个ZIP压缩包
            # 图片存储在 word/media/ 目录中
            with zipfile.ZipFile(file_path, 'r') as docx_zip:
                # 列出所有文件
                file_list = docx_zip.namelist()
                
                # 筛选出media目录中的图片文件
                image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
                media_files = [f for f in file_list if f.startswith('word/media/')]
                
                for media_file in media_files:
                    # 检查是否为图片文件
                    file_ext = Path(media_file).suffix.lower()
                    if file_ext in image_extensions:
                        try:
                            # 提取图片到临时文件
                            image_data = docx_zip.read(media_file)
                            
                            # 创建临时文件
                            temp_image_path = os.path.join(
                                self.temp_dir,
                                f"docx_extracted_{len(self._temp_images)}_{Path(media_file).name}"
                            )
                            
                            # 保存图片
                            with open(temp_image_path, 'wb') as temp_file:
                                temp_file.write(image_data)
                            
                            image_paths.append(temp_image_path)
                            self._temp_images.append(temp_image_path)
                            
                        except Exception as e:
                            print(f"警告：无法提取图片 {media_file}: {e}")
        
        except Exception as e:
            print(f"警告：从DOCX提取图片失败: {e}")
        
        return image_paths
    
    def _extract_images_from_pdf(self, file_path: str) -> List[str]:
        """
        从PDF文件中提取图片
        
        如果启用pdf_screenshot_pages，对于包含图片的页面会进行整页截图
        否则提取页面中的单个图片
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            提取的图片文件路径列表（或页面截图路径列表）
        """
        image_paths = []
        
        # 优先使用PyMuPDF (fitz)，功能最强大
        if PYMUPDF_SUPPORT:
            try:
                pdf_document = fitz.open(file_path)
                
                # 如果启用页面截图模式
                if self.pdf_screenshot_pages:
                    for page_num in range(len(pdf_document)):
                        page = pdf_document[page_num]
                        
                        # 检测页面是否包含图片
                        image_list = page.get_images(full=True)
                        
                        # 如果页面包含图片，对整个页面进行截图
                        if image_list:
                            try:
                                # 计算缩放因子（根据DPI）
                                zoom = self.pdf_screenshot_dpi / 72.0
                                mat = fitz.Matrix(zoom, zoom)
                                
                                # 渲染页面为图片
                                pix = page.get_pixmap(matrix=mat)
                                
                                # 创建临时文件
                                temp_image_path = os.path.join(
                                    self.temp_dir,
                                    f"pdf_page_{page_num + 1}_screenshot.png"
                                )
                                
                                # 保存截图
                                pix.save(temp_image_path)
                                
                                image_paths.append(temp_image_path)
                                self._temp_images.append(temp_image_path)
                                
                                print(f"已对PDF第{page_num + 1}页进行截图（包含{len(image_list)}个图片）")
                                
                                # 若开启图片区域裁剪，则同时裁切页面中每个图片的矩形区域
                                if self.image_region_crops:
                                    try:
                                        # 使用 rawdict 获取图片块的 bbox
                                        raw = page.get_text("rawdict")
                                        img_rects = []
                                        for b in raw.get("blocks", []):
                                            # type 1 为图片块
                                            if b.get("type") == 1 and "bbox" in b:
                                                bbox = b["bbox"]  # [x0, y0, x1, y1]
                                                # 构造矩形并以相同缩放裁剪渲染
                                                rect = fitz.Rect(bbox)
                                                clip_pix = page.get_pixmap(matrix=mat, clip=rect)
                                                crop_path = os.path.join(
                                                    self.temp_dir,
                                                    f"pdf_page_{page_num + 1}_image_{len(img_rects) + 1}_crop.png"
                                                )
                                                clip_pix.save(crop_path)
                                                image_paths.append(crop_path)
                                                self._temp_images.append(crop_path)
                                                img_rects.append(rect)
                                    except Exception as e:
                                        print(f"警告：PDF第{page_num+1}页图片区域裁剪失败: {e}")
                                
                            except Exception as e:
                                print(f"警告：无法对PDF第{page_num+1}页进行截图: {e}")
                
                else:
                    # 原有逻辑：提取单个图片
                    image_index = 0
                    for page_num in range(len(pdf_document)):
                        page = pdf_document[page_num]
                        
                        # 获取页面中的所有图片
                        image_list = page.get_images(full=True)
                        
                        for img_index, img in enumerate(image_list):
                            try:
                                # 获取图片的xref（交叉引用）
                                xref = img[0]
                                
                                # 提取图片数据
                                base_image = pdf_document.extract_image(xref)
                                image_bytes = base_image["image"]
                                image_ext = base_image["ext"]
                                
                                # 创建临时文件
                                temp_image_path = os.path.join(
                                    self.temp_dir,
                                    f"pdf_extracted_{len(self._temp_images)}_{image_index}.{image_ext}"
                                )
                                
                                # 保存图片
                                with open(temp_image_path, 'wb') as temp_file:
                                    temp_file.write(image_bytes)
                                
                                image_paths.append(temp_image_path)
                                self._temp_images.append(temp_image_path)
                                image_index += 1
                                
                            except Exception as e:
                                print(f"警告：无法提取PDF第{page_num+1}页的图片{img_index}: {e}")
                
                pdf_document.close()
                
            except Exception as e:
                print(f"警告：使用PyMuPDF处理PDF图片失败: {e}")
                # 如果PyMuPDF失败，尝试其他方法
                if not self.pdf_screenshot_pages:
                    image_paths = self._extract_images_from_pdf_fallback(file_path)
        
        else:
            # 如果未安装PyMuPDF，且启用了截图模式，提示用户
            if self.pdf_screenshot_pages:
                print("警告：需要安装PyMuPDF才能使用页面截图功能，将回退到备用提取方法")
            
            # 使用备用方法
            image_paths = self._extract_images_from_pdf_fallback(file_path)
        
        return image_paths
    
    def _extract_images_from_pdf_fallback(self, file_path: str) -> List[str]:
        """
        从PDF提取图片的备用方法（使用PyPDF2）
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            提取的图片文件路径列表
        """
        image_paths = []
        
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        # PyPDF2的图片提取功能有限
                        # 需要访问页面资源中的XObject
                        if '/Resources' in page and '/XObject' in page['/Resources']:
                            resources = page['/Resources']
                            x_object = resources['/XObject'].get_object() if '/XObject' in resources else {}
                            
                            if isinstance(x_object, dict):
                                for obj_name in x_object:
                                    obj = x_object[obj_name]
                                    
                                    # 确保是间接对象
                                    if hasattr(obj, 'get_object'):
                                        obj = obj.get_object()
                                    
                                    # 检查是否为图片对象
                                    if isinstance(obj, dict) and obj.get('/Subtype') == '/Image':
                                        try:
                                            # 获取图片数据
                                            if hasattr(obj, 'get_data'):
                                                image_data = obj.get_data()
                                            else:
                                                # PyPDF2 的旧版本可能需要不同的方法
                                                image_data = obj._data if hasattr(obj, '_data') else None
                                            
                                            if not image_data:
                                                continue
                                            
                                            # 尝试确定图片格式
                                            image_filter = obj.get('/Filter', '')
                                            if isinstance(image_filter, list):
                                                image_filter = image_filter[0] if image_filter else ''
                                            
                                            if 'DCTDecode' in str(image_filter) or '/DCTDecode' in str(image_filter):
                                                ext = 'jpg'
                                            elif 'JPXDecode' in str(image_filter) or '/JPXDecode' in str(image_filter):
                                                ext = 'jp2'
                                            else:
                                                ext = 'png'  # 默认PNG
                                            
                                            # 创建临时文件
                                            temp_image_path = os.path.join(
                                                self.temp_dir,
                                                f"pdf_extracted_{len(self._temp_images)}_{page_num}_{obj_name.replace('/', '_')}.{ext}"
                                            )
                                            
                                            # 保存图片
                                            with open(temp_image_path, 'wb') as temp_file:
                                                temp_file.write(image_data)
                                            
                                            image_paths.append(temp_image_path)
                                            self._temp_images.append(temp_image_path)
                                        
                                        except Exception as e:
                                            print(f"警告：无法提取图片对象 {obj_name}: {e}")
                    
                    except Exception as e:
                        print(f"警告：处理PDF第{page_num+1}页时出错: {e}")
        
        except Exception as e:
            print(f"警告：备用PDF图片提取方法失败: {e}")
        
        return image_paths
    
    def cleanup_temp_images(self):
        """清理临时图片文件"""
        for temp_path in self._temp_images:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as e:
                print(f"警告：无法删除临时文件 {temp_path}: {e}")
        
        self._temp_images.clear()
    
    def image_to_base64(self, image_path: str) -> str:
        """将图片转换为Base64编码"""
        if not IMAGE_SUPPORT:
            raise ImportError("需要安装 Pillow: pip install Pillow")
        
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
            # 确定图片格式
            try:
                img = Image.open(image_path)
                format_name = img.format.lower() if img.format else 'png'
            except:
                format_name = Path(image_path).suffix[1:].lower() or 'png'
            
            return f"data:image/{format_name};base64,{base64_data}"
    
    def split_file(self, file_path: str) -> List[MultimodalChunk]:
        """
        分割文件为多模态块
        
        Args:
            file_path: 文件路径
            
        Returns:
            多模态分块列表
        """
        chunks = []
        file_path = os.path.abspath(file_path)
        modality = self.detect_modality(file_path)
        
        if modality == 'image':
            # 图片文件：直接作为一个块
            base64_image = self.image_to_base64(file_path)
            chunks.append(MultimodalChunk(
                id=1,
                content=base64_image,
                modality_type='image',
                metadata={
                    'file_path': file_path,
                    'file_name': os.path.basename(file_path),
                    'file_size': os.path.getsize(file_path)
                }
            ))
        
        elif modality == 'video':
            # 视频文件：直接作为一个块（使用文件路径或URL）
            chunks.append(MultimodalChunk(
                id=1,
                content=file_path,  # 实际应用中可能需要URL
                modality_type='video',
                metadata={
                    'file_path': file_path,
                    'file_name': os.path.basename(file_path),
                    'file_size': os.path.getsize(file_path)
                }
            ))
        
        elif modality == 'text':
            # 文本文件：分块处理
            text = self.read_text_file(file_path)
            text_chunks = self.split_text(text)
            
            for i, chunk_text in enumerate(text_chunks, 1):
                chunks.append(MultimodalChunk(
                    id=i,
                    content=chunk_text,
                    modality_type='text',
                    metadata={
                        'file_path': file_path,
                        'file_name': os.path.basename(file_path),
                        'chunk_index': i,
                        'total_chunks': len(text_chunks)
                    }
                ))
        
        elif modality == 'multimodal':
            # 混合模态文件（如DOCX、PDF）
            ext = Path(file_path).suffix.lower()
            
            # 提取文本和图片
            if ext == '.docx':
                text, image_paths = self.read_docx(file_path)
            elif ext == '.pdf':
                text, image_paths = self.read_pdf(file_path)
            else:
                # 其他格式按文本处理
                text = self.read_text_file(file_path)
                image_paths = []
            
            chunk_id = 1
            
            # 处理文本分块：使用优化的语义分块器
            if text.strip():
                if self.use_semantic_splitter:
                    # 使用优化的语义分块器
                    if ext == '.docx':
                        text_chunks = semantic_split_docx(
                            file_path,
                            min_chars=self.min_chars,
                            max_chars=self.max_chars,
                            window_size=self.window_size,
                            smoothing_width=self.smoothing_width,
                            chunk_size=self.chunk_size
                        )
                    elif ext == '.pdf':
                        text_chunks = semantic_split_pdf(
                            file_path,
                            min_chars=self.min_chars,
                            max_chars=self.max_chars,
                            window_size=self.window_size,
                            smoothing_width=self.smoothing_width,
                            chunk_size=self.chunk_size
                        )
                    else:
                        text_chunks = split_text_to_chunks(
                            text,
                            min_chars=self.min_chars,
                            max_chars=self.max_chars,
                            window_size=self.window_size,
                            smoothing_width=self.smoothing_width,
                            chunk_size=self.chunk_size
                        )
                else:
                    # 使用基础文本分块
                    text_chunks = self.split_text(text)
                
                # 添加文本分块
                for i, chunk_text in enumerate(text_chunks, 1):
                    chunks.append(MultimodalChunk(
                        id=chunk_id,
                        content=chunk_text,
                        modality_type='text',
                        metadata={
                            'file_path': file_path,
                            'file_name': os.path.basename(file_path),
                            'chunk_index': i,
                            'total_text_chunks': len(text_chunks),
                            'chunk_method': 'semantic' if self.use_semantic_splitter else 'basic'
                        }
                    ))
                    chunk_id += 1
            
            # 处理图片：保留路径，不转换为base64
            for img_index, img_path in enumerate(image_paths, 1):
                try:
                    # 图片内容使用路径标识，不存储base64
                    # 前端可以根据这个路径加载图片
                    image_identifier = f"image_{img_index}_{Path(img_path).name}"
                    
                    # 判断是否是页面截图（通过文件名判断）
                    is_pdf_screenshot = 'pdf_page' in Path(img_path).name and 'screenshot' in Path(img_path).name
                    is_docx_screenshot = 'docx_page' in Path(img_path).name and 'screenshot' in Path(img_path).name
                    is_page_screenshot = is_pdf_screenshot or is_docx_screenshot
                    
                    metadata = {
                        'file_path': file_path,
                        'image_path': img_path,  # 原始图片路径
                        'image_identifier': image_identifier,
                        'file_name': os.path.basename(file_path),
                        'original_file': os.path.basename(file_path),
                        'image_index': img_index,
                        'total_images': len(image_paths),
                        'image_name': Path(img_path).name,
                        'image_size': os.path.getsize(img_path) if os.path.exists(img_path) else 0,
                        'is_page_screenshot': is_page_screenshot
                    }
                    
                    # 如果是PDF页面截图，尝试提取页面号
                    if is_pdf_screenshot:
                        import re
                        match = re.search(r'pdf_page_(\d+)_screenshot', Path(img_path).name)
                        if match:
                            metadata['pdf_page_number'] = int(match.group(1))
                    
                    # 如果是Word页面截图，尝试提取页面号
                    if is_docx_screenshot:
                        import re
                        match = re.search(r'docx_page_(\d+)_screenshot', Path(img_path).name)
                        if match:
                            metadata['docx_page_number'] = int(match.group(1))
                            metadata['pdf_page_number'] = int(match.group(1))  # 也保留pdf_page_number以便统一处理
                    
                    chunks.append(MultimodalChunk(
                        id=chunk_id,
                        content=image_identifier,  # 使用标识符而非base64
                        modality_type='image',
                        metadata=metadata
                    ))
                    chunk_id += 1
                except Exception as e:
                    print(f"警告：无法处理图片 {img_path}: {e}")
        
        # 注意：临时文件会在对象销毁时或手动调用cleanup_temp_images时清理
        # 如果需要立即清理，可以调用 self.cleanup_temp_images()
        
        return chunks
    
    def split_to_dict(self, file_path: str) -> List[Dict]:
        """分割文件并返回字典列表（用于JSON序列化）"""
        chunks = self.split_file(file_path)
        return [asdict(chunk) for chunk in chunks]


def main():
    """测试示例"""
    splitter = MultimodalSpilter(
        text_chunk_size=1000,
        text_chunk_overlap=200,
        extract_images=True
    )
    
    # 测试文本文件
    test_file = "test.txt"
    if os.path.exists(test_file):
        chunks = splitter.split_file(test_file)
        for chunk in chunks:
            print(f"块 {chunk.id}: [{chunk.modality_type}] {chunk.content[:50]}...")
    else:
        print(f"测试文件不存在: {test_file}")


if __name__ == "__main__":
    main()

