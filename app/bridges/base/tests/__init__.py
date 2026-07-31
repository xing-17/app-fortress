"""
Bridges Resources Base Tests

包含 app.bridges.base 模块的全面测试套件：

- test_registry_all.py: BaseRegistry 的测试（持久化、查询、更新）
- test_service_all.py: BaseBridgesService 的测试（任务队列、工作线程）
- test_servicehealth_all.py: ServiceHealth 的测试（健康状态监控）
- test_state_all.py: BaseBridgesState 的测试（状态管理、转换）

运行所有测试：
    pytest app/bridges/resources/base/tests/

运行特定测试文件：
    pytest app/bridges/resources/base/tests/test_service_all.py
"""
