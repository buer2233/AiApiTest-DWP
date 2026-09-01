# 三期验证批处理报告

- 运行时间：2026-08-19 14:03:19

- ✅ **T3.3 评估集静态校验**：无校验错误
- ✅ **T3.3 探针冒烟（3 条）**：判定全部符合预期
- ✅ **T3.3 触发成功率实跑**：accuracy=1.0, inconclusive=0, passed=22/22（正例命中与负例不误触均可复现）
- ✅ **T3.3/T3.4 框架测试**：...................                                                      [100%]Running teardown with pytest sessionfinish... |  | 19 passed in 1.28s
- ✅ **T3.7 分析 CLI 测试套件**：.                                                                        [100%]Running teardown with pytest sessionfinish... |  | 73 passed in 3.09s
- ✅ **T3.4 凭据文件不再被忽略**：config.json 与 test_data/account.json 均可提交
- ✅ **T3.4 提交前审计**：Git �ύ׼�����ͨ��
- ✅ **简体中文独立验收项**：��������˵��У��ͨ����
- ✅ **T3.5 inventory 新路径实跑**：D:\AI\E9_svn_analyse\api-test-E9\E9_svn_analyse\output\_inventory.json
- ✅ **T3.5 render 新路径实跑**：fixture r999999：D:\AI\E9_svn_analyse\api-test-E9\E9_svn_analyse\output\r999999\report.html
- ✅ **T3.10 git-branch 决策树实操**：当前分支 master → 新建并切到 eval/t3-probe → 切回 master → 已删除本次创建的临时分支
- ✅ **T3.5/T3.10 analyse r349149（本地 MCP 全链路)**：confidence=high, endpoints=13, impact_rows=2, warnings=0, 48.2s（MCP 查询正常）
- ✅ **T3.10 阶段 C 执行 r349149**：4 passed, 9 deselected in 1.36s

合计：13/13 项通过。
