# 上游来源

本包是项目的调用、验证与交付封装，实际加载独立安装的上游模型。发行本包不包含EGMOF/MOFFlow-2源码、模型权重、数据集或第三方可执行文件；这些资产按runtime路径引用。

- EGMOF源码：Yeonghun Kang，MIT许可证。来源：https://github.com/Yeonghun1675/EGMOF ，许可：https://github.com/Yeonghun1675/EGMOF/blob/main/LICENSE 。使用/再分发上游软件应保留其版权及许可声明。
- EGMOF官方预训练权重：Zenodo 19362907，元数据标注CC BY 4.0；来源：https://zenodo.org/records/19362907 。按对应许可署名、链接许可并标明修改。本封装未修改权重，也不宣称由上游为封装结果背书。
- MOFFlow-2、PORMAKE、MACE、ASE、RDKit、MOFid等使用各自现有安装。发布包含这些依赖或权重的整套产品前，分别记录实际版本、许可证与分发义务；EGMOF的许可不替代依赖许可。

场景名称及数值以配置中的原模型性质为准。示例场景不代表已针对其他气体或分离任务训练。
