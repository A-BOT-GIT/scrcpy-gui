"""scrcpy-gui 逻辑层包（MVP Presenter / 状态机 / 信号契约）。

本包承载重构后的逻辑层：``AppController``（MVP Presenter）、
``ConnectionStateMachine``（连接状态机）以及本阶段确立的接口契约
``signals``。视图层（``ui/``）与工具层（``core/``）均不得反向依赖本包实现细节。
"""

__version__ = "0.1.0"
