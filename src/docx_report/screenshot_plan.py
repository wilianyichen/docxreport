from __future__ import annotations

from .models import ReportConfig


def generate_screenshot_plan(config: ReportConfig) -> list[dict[str, str]]:
    plan: list[dict[str, str]] = []
    for index, block in enumerate(config.blocks, start=1):
        if block.kind != "placeholder":
            continue
        plan.append(
            {
                "index": str(index),
                "placeholder": block.text,
                "source": str(block.meta.get("source", "manual-capture")),
                "target": str(block.meta.get("target", config.output)),
                "mode": str(block.meta.get("mode", "placeholder-only")),
            }
        )
    return plan


def summarize_course_report_patterns(config: ReportConfig) -> dict[str, object]:
    placeholder_count = sum(1 for block in config.blocks if block.kind == "placeholder")
    image_slot_count = sum(1 for block in config.blocks if block.kind == "image")
    section_count = sum(1 for block in config.blocks if block.kind == "section")
    subheading_count = sum(1 for block in config.blocks if block.kind == "subheading")

    common_flow = [
        "读取实验配置",
        "确认模板或现有报告布局",
        "写入封面标题与实验名称",
        "按 blocks 渲染正文结构",
        "执行截图/图片相关处理",
        "运行结构和可打开性校验",
    ]

    mode_traits = {
        "single_report": [
            "聚焦一个实验目录的结果、截图和文字修订",
            "允许针对该实验插入特定指标和说明",
            "更关注当前报告是否与现有结果一致",
        ],
        "cross_course_common": [
            "依赖统一模板表格定位",
            "复用 section/body/subheading/placeholder/image 这类 blocks",
            "共享 build / revise / enrich / validate 四段式工作流",
            "共享 run 分裂处理和模板结构检查",
        ],
        "scenario_specific": [
            "占位型报告：placeholder 数量较多，适合先产出骨架",
            "保图修订型报告：image slot 与 expected_images 更关键",
            "富化型报告：更依赖 anchor、图表路径和附录注入",
        ],
    }

    return {
        "report": config.name,
        "backend": config.backend,
        "counts": {
            "sections": section_count,
            "subheadings": subheading_count,
            "placeholders": placeholder_count,
            "image_slots": image_slot_count,
        },
        "common_flow": common_flow,
        "mode_traits": mode_traits,
        "specific_focus": {
            "expected_images": config.expected_images,
            "has_placeholders": placeholder_count > 0,
            "has_image_slots": image_slot_count > 0,
        },
    }
