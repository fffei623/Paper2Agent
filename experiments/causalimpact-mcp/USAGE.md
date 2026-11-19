# CausalImpact MCP 使用说明

本 MCP 服务提供一个面向新时间序列的分析工具 `analyze_causal_impact`，底层调用 Google 的 CausalImpact R 包。使用的上游版本为 1.4.1，固定在提交 `0f5bf8d97cfb13321926c68b7eaeec74bb692b61`。

## 工具输入

- `data`：矩形数值表，每一行代表一个时间点。第一列是响应序列，后续列是控制序列。仅响应列允许使用 `null` 表示缺失值。
- `pre_period`、`post_period`：前期和干预后区间的首尾行号，均为包含端点的 1 起始索引。前期必须早于干预后区间。
- `alpha`：后验区间的尾概率，默认值为 `0.05`。
- `model_args`：可选的原包模型参数子集：`niter`、`standardize.data`、`prior.level.sd`、`nseasons`、`season.duration`、`dynamic.regression`、`max.flips`。
- `seed`：可选的 R 随机种子。提供时会为原生 R 计算设置随机种子。
- `column_names`：响应序列和控制序列的可选列名，必须唯一且与数据列数一致。

工具调用 `CausalImpact::CausalImpact()`，返回原包的汇总和报告、按时间索引的完整结果序列，以及 CSV 和 PDF 文件的绝对路径。每次调用都会在 `tests/results/tool-runs/` 下创建独立目录。

## 运行环境与安装

已验证的开发环境为 Windows x64、R 4.6.2、renv 1.3.1、Python 3.14.7 和 FastMCP 4.0.3。R 版本需为 4.5.0 或更新版本。CausalImpact 依赖 `bsts`、`Boom`、`BoomSpikeSlab`、`ggplot2`、`zoo` 以及锁文件中记录的其他依赖。

1. 安装 R 4.5 或更新版本，并确保命令行可以运行 `Rscript`。Windows 上若 CRAN 提供匹配的二进制包，通常不需要本地安装 Rtools。
2. 在本目录下，根据锁文件恢复项目 R 库：

   ```powershell
   Rscript --vanilla -e "source('renv/activate.R'); renv::restore(prompt=FALSE)"
   ```

3. 从随包保留的固定提交源码安装 CausalImpact，确保运行时使用指定的上游源码：

   ```powershell
   Rscript --vanilla -e "source('renv/activate.R'); install.packages('repo/CausalImpact', repos=NULL, type='source')"
   ```

4. 创建 Python 环境并安装 `src/requirements.txt` 中的依赖。
5. 通过标准输入输出方式启动 MCP 服务：

   ```powershell
   .\CausalImpact-env\Scripts\python.exe src\causalimpact_mcp.py
   ```

启动器优先使用项目内的 R 可执行文件；若该文件不存在，则从系统 `PATH` 查找 `Rscript`。renv 项目默认使用当前目录。需要切换运行环境时，可设置 `P2A_RSCRIPT` 和 `P2A_R_PROJECT`。Windows 上 R 临时目录路径不能包含空格；如果项目路径含空格，启动器会自动选择不含空格的临时目录。可通过 `P2A_R_TEMP_DIR` 指定其他临时目录。请勿将服务指向无关的用户级 R 库。

## 科学解释的适用边界

该方法假设控制序列未受到干预影响，并且响应序列与控制序列在前期的关系在干预后仍然稳定。这些是需要用户结合实际场景判断的实质性假设；程序正常运行或通过软件检查并不能证明假设成立。MCMC 输出具有随机性，数值比较应使用有依据的容差，不应要求结果文本完全一致。

当前参考运行覆盖官方提供的 100 个观测值合成示例，不代表复现了论文中的全部模拟实验或在线广告分析。
