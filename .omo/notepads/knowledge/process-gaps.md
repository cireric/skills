# 流程缺陷记录

从 info-collector-improvement 项目中观察到的流程缺陷。

## notepad 机制未被实际使用

整个开发过程中 notepad 四个文件全部为空。根因：
1. hook 注入用 "SHOULD" 而非 "MUST"，模型未强制写入
2. 编排者未在子代理完成后检查 notepad
3. 编排者未在派发前读取 notepad 注入上下文
4. 上下文窗口够用时不触发持久化需求

**影响**：会话被 compaction 或中断时，跨任务知识传递完全依赖上下文窗口，无持久化备份。

**缓解**：在每个 wave 完成后由编排者主动写入 notepad。
