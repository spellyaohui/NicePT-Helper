# 语言规则

## 中文优先原则

除代码文件外，所有交互和文档都使用中文：

- **用户交互**：所有回复、说明、建议使用中文
- **注释和文档**：Markdown 文档、README、设计文档使用中文
- **提交信息**：Git commit 信息使用中文
- **日志输出**：应用程序日志消息使用中文

## 代码文件规范

代码文件保持英文：

- 变量名、函数名、类名使用英文
- 代码注释可以使用中文，便于理解复杂逻辑
- API 端点路径使用英文
- 数据库字段名使用英文

## 示例

```python
# 正确：代码用英文，注释可用中文
def refresh_account_data(account_id: int):
    """刷新账号数据"""
    # 从 PT 站点获取最新统计信息
    stats = site_adapter.get_user_stats(account_id)
    return stats

# 错误：不要使用拼音或中文作为标识符
def shuaxin_zhanghu(账号ID):
    pass
```

## 文档类型

- ✅ 中文：README.md、设计文档、需求文档、用户手册
- ✅ 中文：Steering 规则文档
- ✅ 中文：与用户的所有对话
- ❌ 英文：Python/JavaScript 代码标识符
- ⚠️ 混合：代码注释（英文代码 + 中文注释）
