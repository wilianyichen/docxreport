"""按课程范式生成 report config 骨架。

目的：把「跨实验完全相同的骨架」交给代码生成，人只写本次实验特有的内容（题目与结果解读），
从而显著降低每次写报告要产出的文本量。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .course_profile import is_course_profile, read_structured_file
from .errors import CourseProfileError

CN_DIGITS = "零一二三四五六七八九"


def cn_number(n: int) -> str:
    if n <= 0:
        return str(n)
    if n < 10:
        return CN_DIGITS[n]
    if n == 10:
        return "十"
    if n < 20:
        return "十" + CN_DIGITS[n % 10]
    return CN_DIGITS[n // 10] + "十" + (CN_DIGITS[n % 10] if n % 10 else "")


def scaffold_blocks(tasks: int) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    blocks.append({"kind": "section", "text": "一、实验目的"})
    blocks.append({"kind": "body", "text": "【待填写：本实验要回答的问题，以及必须走完的流程。】"})
    blocks.append({"kind": "section", "text": "二、实验原理"})
    blocks.append({"kind": "body", "text": "【待填写：任务定位、方法原理、评价指标与决策阈值的含义。】"})
    blocks.append({"kind": "section", "text": "三、实验环境"})
    blocks.append(
        {
            "kind": "body",
            "text": "【待填写：实测环境版本。操作系统；解释器绝对路径与版本；框架与库版本号；绘图字体。不得照抄指导书。】",
        }
    )
    blocks.append({"kind": "section", "text": "四、实验步骤"})
    blocks.append({"kind": "body", "text": "【待填写：按指导书的作业顺序列出操作步骤与关键参数。】"})
    blocks.append({"kind": "section", "text": "五、实验过程和结果记录，以及结果解析"})
    for t in range(1, tasks + 1):
        blocks.append({"kind": "subheading", "text": f"作业{t} 【待填写：作业标题】"})
        blocks.append({"kind": "body", "text": f"【分析代码：作业{t} 用了哪些函数与参数。】"})
        blocks.append(
            {"kind": "placeholder", "text": f"【图片占位｜运行截图：Notebook 代码单元 #{t} 的运行输出】"}
        )
        blocks.append(
            {"kind": "caption", "text": f"运行截图{t}：【待填写：这条运行截图展示了什么，关键数值是多少。】"}
        )
        blocks.append(
            {
                "kind": "body",
                "text": f"【运行结果数据：作业{t} 的实测数字，建议改用 kind: metrics 从 results/metrics.json 读取。】",
            }
        )
        blocks.append({"kind": "body", "text": f"【结果解读：作业{t} 的结论、异常点、以及不能下的结论。】"})
    blocks.append({"kind": "section", "text": "六、实验总结"})
    for _ in range(4):
        blocks.append(
            {
                "kind": "body",
                "text": "【待填写：具体到哪一步出错、哪个数字与预期不符、哪些结论不能下。禁止套话与拔高。】",
            }
        )
    return blocks


def scaffold_report_config(
    profile_path: Path,
    experiment_no: int,
    out_path: Path,
    *,
    tasks: int = 6,
    experiment_name: str = "【待填写：实验题目】",
) -> Path:
    profile_path = Path(profile_path)
    profile = read_structured_file(profile_path)
    if not is_course_profile(profile):
        raise CourseProfileError(f"{profile_path}: kind != 'course-report-profile'")

    course = profile.get("course") or {}
    naming = profile.get("naming") or {}
    template_name = str(naming.get("template_filename") or "实验报告模板.docx")
    report_pattern = str(naming.get("report_filename") or "实验报告{N}.docx")

    out_path = Path(out_path)
    experiment_dir = out_path.parent.parent if out_path.parent.name.lower() == "docs" else out_path.parent
    course_root = profile_path.parent
    template_path = course_root / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"template not found under course root: {template_path}")
    rel_template = os.path.relpath(template_path, experiment_dir).replace("\\", "/")

    raw: dict[str, Any] = {
        "name": f"experiment{experiment_no}",
        "backend": "ooxml-template",
        "template": rel_template,
        "output": report_pattern.format(N=experiment_no),
        "cover_title": str(course.get("cover_title_pattern") or "实验{N}").format(
            N=experiment_no, cn_num=cn_number(experiment_no)
        ),
        "experiment_name": experiment_name,
        "expected_images": tasks,
    }
    assumptions = profile.get("template_assumptions")
    if isinstance(assumptions, dict):
        raw["assumptions"] = assumptions
    raw["blocks"] = scaffold_blocks(tasks)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# {course.get('name', '')} · 第 {experiment_no} 次实验报告配置（由 skill scaffold 生成）\n"
        f"# 样式 / 结构 / 图片规范继承课程范式：{profile_path.name}（自动向上查找，无需在此重复声明）\n"
        f"# 需要人工填写的只有：experiment_name、标记为【待填写】的段落、以及用 kind: figure 补结果图\n"
    )
    body = yaml.safe_dump(raw, allow_unicode=True, sort_keys=False, default_flow_style=False, width=100)
    out_path.write_text(header + body, encoding="utf-8")
    return out_path
