# utils.py
import pandas as pd
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class EnterpriseUserValidator:
    """企业用户验证器"""

    def __init__(self, excel_path=None):
        """
        初始化验证器

        Args:
            excel_path: Excel文件路径，如果不提供则使用settings中的配置
        """
        if excel_path is None:
            excel_path = getattr(settings, 'ENTERPRISE_USERS_EXCEL_PATH',
                                 os.path.join(settings.BASE_DIR, 'data', 'enterprise_users.xlsx'))

        self.excel_path = excel_path
        self._df = None

    def _load_excel(self):
        """加载Excel文件"""
        if self._df is not None:
            return self._df

        try:
            if not os.path.exists(self.excel_path):
                logger.error(f"企业用户Excel文件不存在: {self.excel_path}")
                raise FileNotFoundError(f"企业用户数据文件不存在")

            # 读取Excel文件，支持.xlsx和.xls格式
            self._df = pd.read_excel(self.excel_path)

            # 验证必要的列是否存在
            required_columns = ['姓名', '工号']  # 可根据实际Excel表头调整
            missing_columns = [col for col in required_columns if col not in self._df.columns]

            if missing_columns:
                # 尝试其他可能的列名
                alternative_names = {
                    '姓名': ['name', 'username', '员工姓名', '姓名'],
                    '工号': ['employee_id', 'emp_id', 'id', '员工编号', '工号']
                }

                # 标准化列名
                column_mapping = {}
                for req_col in required_columns:
                    for alt_name in alternative_names.get(req_col, []):
                        if alt_name in self._df.columns:
                            column_mapping[alt_name] = req_col
                            break

                if column_mapping:
                    self._df.rename(columns=column_mapping, inplace=True)
                else:
                    raise ValueError(f"Excel文件缺少必要的列: {missing_columns}")

            # 数据清洗：去除空值和前后空格
            self._df['姓名'] = self._df['姓名'].astype(str).str.strip()
            self._df['工号'] = self._df['工号'].astype(str).str.strip()

            # 过滤掉空行
            self._df = self._df[
                (self._df['姓名'] != '') &
                (self._df['姓名'] != 'nan') &
                (self._df['工号'] != '') &
                (self._df['工号'] != 'nan')
                ]

            logger.info(f"成功加载企业用户数据，共 {len(self._df)} 条记录")
            return self._df

        except Exception as e:
            logger.error(f"加载企业用户Excel文件失败: {e}")
            raise Exception(f"加载企业用户数据失败: {str(e)}")

    def validate_enterprise_user(self, name, employee_id):
        """
        验证企业用户是否存在

        Args:
            name: 员工姓名
            employee_id: 工号

        Returns:
            dict: {
                'valid': bool,  # 是否验证通过
                'message': str,  # 提示信息
                'user_info': dict or None  # 用户信息（如果验证通过）
            }
        """
        try:
            df = self._load_excel()

            # 清洗输入数据
            name = str(name).strip()
            employee_id = str(employee_id).strip()

            if not name or not employee_id:
                return {
                    'valid': False,
                    'message': '姓名和工号不能为空',
                    'user_info': None
                }

            # 查找匹配的记录
            match = df[
                (df['姓名'] == name) &
                (df['工号'] == employee_id)
                ]

            if not match.empty:
                # 找到匹配记录
                user_info = match.iloc[0].to_dict()
                return {
                    'valid': True,
                    'message': '验证成功',
                    'user_info': {
                        'name': user_info.get('姓名'),
                        'employee_id': user_info.get('工号'),
                        # 可以添加更多字段，如部门、职位等
                        'department': user_info.get('部门', None),
                        'position': user_info.get('职位', None),
                    }
                }
            else:
                # 检查是否只有姓名匹配
                name_match = df[df['姓名'] == name]
                if not name_match.empty:
                    return {
                        'valid': False,
                        'message': '工号与姓名不匹配，请检查工号是否正确',
                        'user_info': None
                    }

                # 检查是否只有工号匹配
                id_match = df[df['工号'] == employee_id]
                if not id_match.empty:
                    return {
                        'valid': False,
                        'message': '姓名与工号不匹配，请检查姓名是否正确',
                        'user_info': None
                    }

                # 都不匹配
                return {
                    'valid': False,
                    'message': '还没有您的信息，请联系相关人员',
                    'user_info': None
                }

        except Exception as e:
            logger.error(f"验证企业用户失败: {e}")
            return {
                'valid': False,
                'message': f'验证失败: {str(e)}',
                'user_info': None
            }

    def reload_data(self):
        """重新加载Excel数据（用于数据更新后刷新缓存）"""
        self._df = None
        return self._load_excel()

