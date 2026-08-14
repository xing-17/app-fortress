请帮我为这个模块补全测试和doctring
/Users/xingxing/Desktop/PROJECT/apps/app-fortress/package/lib-bastion/bastion/domain/bridge

要求每一个python文件对应一个测试
文件格式要求例子
|-- run/ 
    |-- run.py
    |-- __init__.py
    |-- tests/
       |-- __init__.py
       |-- test_run_unit.py
测试要求确认正确性即可不必过于复杂
docstring格式要求符合行业最佳实践
class statement明确列出 description attr method example即可
格式为
"""
<description>

Attributes:
    <attr_name> (<attr_type>): <attr_description>
    ...

Methods:
    <method_name>(<param_type> <param_name>, ...): <method_description>
    ...

Example:
    ```python

        <example_code>
    ```

"""
method 只需要列出description
格式为
"""
...
"""
要求desciption简单直接 最好一句话概括
不需要导出summary 
