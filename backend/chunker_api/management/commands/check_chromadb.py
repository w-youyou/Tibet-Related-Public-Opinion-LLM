"""
Django 管理命令：检查 ChromaDB 向量数据库的状态
用于诊断 RAG 系统检索问题

使用方法:
    python manage.py check_chromadb
    python manage.py check_chromadb --collection multimodal_documents
    python manage.py check_chromadb --test-query "测试问题"
"""

import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = '检查 ChromaDB 向量数据库的状态和内容'

    def add_arguments(self, parser):
        parser.add_argument(
            '--db-path',
            type=str,
            default='./chroma_db',
            help='ChromaDB 数据库路径 (默认: ./chroma_db)'
        )
        parser.add_argument(
            '--collection',
            type=str,
            default='multimodal_documents',
            help='集合名称 (默认: multimodal_documents)'
        )
        parser.add_argument(
            '--test-query',
            type=str,
            help='测试查询语句'
        )
        parser.add_argument(
            '--top-k',
            type=int,
            default=5,
            help='检索结果数量 (默认: 5)'
        )

    def handle(self, *args, **options):
        db_path = options['db_path']
        collection_name = options['collection']
        test_query = options.get('test_query')
        top_k = options['top_k']

        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('ChromaDB 向量数据库诊断工具'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')

        # 1. 检查数据库路径
        self.stdout.write(self.style.WARNING('【步骤 1】检查数据库路径'))
        self.stdout.write(f'数据库路径: {db_path}')
        
        if os.path.exists(db_path):
            self.stdout.write(self.style.SUCCESS('✓ 数据库目录存在'))
            
            # 列出目录内容
            try:
                files = os.listdir(db_path)
                self.stdout.write(f'  目录内容: {", ".join(files) if files else "(空)"}')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  无法读取目录: {e}'))
        else:
            self.stdout.write(self.style.ERROR('✗ 数据库目录不存在'))
            self.stdout.write(self.style.WARNING('  提示: 您可能还没有上传任何文档'))
            return

        self.stdout.write('')

        # 2. 连接 ChromaDB
        self.stdout.write(self.style.WARNING('【步骤 2】连接 ChromaDB'))
        try:
            import chromadb
            client = chromadb.PersistentClient(path=db_path)
            self.stdout.write(self.style.SUCCESS('✓ 成功连接到 ChromaDB'))
        except ImportError:
            self.stdout.write(self.style.ERROR('✗ chromadb 包未安装'))
            self.stdout.write('  请运行: pip install chromadb')
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 连接失败: {e}'))
            return

        self.stdout.write('')

        # 3. 列出所有集合
        self.stdout.write(self.style.WARNING('【步骤 3】列出所有集合'))
        try:
            collections = client.list_collections()
            if collections:
                self.stdout.write(self.style.SUCCESS(f'✓ 找到 {len(collections)} 个集合:'))
                for coll in collections:
                    self.stdout.write(f'  - {coll.name}')
            else:
                self.stdout.write(self.style.ERROR('✗ 没有找到任何集合'))
                self.stdout.write(self.style.WARNING('  提示: 您可能还没有上传任何文档'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 列出集合失败: {e}'))
            return

        self.stdout.write('')

        # 4. 检查指定集合
        self.stdout.write(self.style.WARNING(f'【步骤 4】检查集合: {collection_name}'))
        try:
            collection = client.get_collection(name=collection_name)
            self.stdout.write(self.style.SUCCESS(f'✓ 集合存在'))
            
            # 获取集合统计信息
            count = collection.count()
            self.stdout.write(f'  文档数量: {count}')
            
            if count == 0:
                self.stdout.write(self.style.ERROR('✗ 集合为空'))
                self.stdout.write(self.style.WARNING('  提示: 请先上传文档并进行向量化'))
                return
            
            # 获取前几条数据查看
            sample_data = collection.get(limit=3)
            
            self.stdout.write('')
            self.stdout.write('  样本数据:')
            if sample_data and sample_data.get('ids'):
                for i, doc_id in enumerate(sample_data['ids']):
                    metadata = sample_data['metadatas'][i] if sample_data.get('metadatas') else {}
                    document = sample_data['documents'][i] if sample_data.get('documents') else ''
                    
                    self.stdout.write(f'    [{i+1}] ID: {doc_id}')
                    self.stdout.write(f'        模态类型: {metadata.get("modality_type", "未知")}')
                    self.stdout.write(f'        文件名: {metadata.get("file_name", "未知")}')
                    
                    if metadata.get('modality_type') == 'text':
                        preview = document[:100] + '...' if len(document) > 100 else document
                        self.stdout.write(f'        内容预览: {preview}')
                    elif metadata.get('modality_type') == 'image':
                        self.stdout.write(f'        图片路径: {metadata.get("image_path", "未知")}')
                    
                    self.stdout.write('')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 获取集合失败: {e}'))
            return

        self.stdout.write('')

        # 5. 测试查询（如果提供了测试问题）
        if test_query:
            self.stdout.write(self.style.WARNING(f'【步骤 5】测试查询: "{test_query}"'))
            
            # 检查 API Key
            api_key = os.environ.get('DASHSCOPE_API_KEY')
            if not api_key:
                self.stdout.write(self.style.ERROR('✗ 未配置 DASHSCOPE_API_KEY'))
                self.stdout.write('  请设置环境变量: export DASHSCOPE_API_KEY="your_key"')
                return
            
            try:
                # 使用 MultimodalEncoder 进行查询
                from views.Spilter.MultimodalEncoder import MultimodalEncoder
                
                encoder = MultimodalEncoder(
                    api_key=api_key,
                    model='tongyi-embedding-vision-plus',
                    chroma_db_path=db_path,
                    collection_name=collection_name
                )
                
                self.stdout.write('  正在查询...')
                results = encoder.query(
                    query_text=test_query,
                    n_results=top_k
                )
                
                if results:
                    self.stdout.write(self.style.SUCCESS(f'✓ 找到 {len(results)} 条结果:'))
                    self.stdout.write('')
                    
                    for i, result in enumerate(results):
                        metadata = result.get('metadata', {})
                        distance = result.get('distance', 0)
                        document = result.get('document', '')
                        
                        self.stdout.write(f'  【结果 {i+1}】')
                        self.stdout.write(f'    相似度距离: {distance:.4f}')
                        self.stdout.write(f'    模态类型: {metadata.get("modality_type", "未知")}')
                        self.stdout.write(f'    文件名: {metadata.get("file_name", "未知")}')
                        
                        if metadata.get('modality_type') == 'text':
                            preview = document[:150] + '...' if len(document) > 150 else document
                            self.stdout.write(f'    内容: {preview}')
                        elif metadata.get('modality_type') == 'image':
                            self.stdout.write(f'    图片: {metadata.get("image_path", "未知")}')
                        
                        self.stdout.write('')
                else:
                    self.stdout.write(self.style.ERROR('✗ 没有找到任何结果'))
                    self.stdout.write(self.style.WARNING('  可能原因:'))
                    self.stdout.write('    1. 问题与文档内容相关度太低')
                    self.stdout.write('    2. 向量化时出现问题')
                    self.stdout.write('    3. 嵌入模型配置不正确')
                
            except ImportError:
                self.stdout.write(self.style.ERROR('✗ MultimodalEncoder 不可用'))
                self.stdout.write('  请确保 MultimodalEncoder.py 在项目根目录')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ 查询失败: {e}'))
                import traceback
                self.stdout.write(traceback.format_exc())

        # 6. 总结
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('诊断完成'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        if count > 0:
            self.stdout.write(self.style.SUCCESS(f'✓ 数据库状态正常，包含 {count} 条文档'))
            if not test_query:
                self.stdout.write('')
                self.stdout.write('提示: 使用 --test-query 参数测试实际查询:')
                self.stdout.write(f'  python manage.py check_chromadb --test-query "你的问题"')
        else:
            self.stdout.write(self.style.WARNING('⚠ 数据库为空，请先上传文档'))
            self.stdout.write('')
            self.stdout.write('上传文档的方法:')
            self.stdout.write('  1. 使用 API: POST /api/chunk/')
            self.stdout.write('  2. 选择 chunker_type: multimodal')
            self.stdout.write('  3. 上传文件')

