from .models import Finding


SCI_TERMS = [
    "spinal cord injury",
    "spinal cord injuries",
    "sci",
    "paralysis",
    "paraplegia",
    "tetraplegia",
    "quadriplegia",
    "spinal cord",
    "травма спинного мозга",
    "травмы спинного мозга",
    "травму спинного мозга",
    "повреждение спинного мозга",
    "спинной мозг",
    "спинного мозга",
    "паралич",
    "параплегия",
    "тетраплегия",
    "тсм",
    "脊髓损伤",
]

RECOVERY_TECH_TERMS = [
    "treatment",
    "therapy",
    "recovery",
    "restore",
    "restoration",
    "motor function",
    "sensation",
    "walking",
    "gait",
    "neurorehabilitation",
    "rehabilitation",
    "clinical trial",
    "phase 1",
    "phase 2",
    "first-in-human",
    "neurostimulation",
    "epidural stimulation",
    "electrical stimulation",
    "spinal stimulation",
    "brain-computer interface",
    "bci",
    "implant",
    "device",
    "neural interface",
    "robot",
    "robotic",
    "exoskeleton",
    "stem cell",
    "cell therapy",
    "cell transplantation",
    "mesenchymal",
    "neural stem",
    "ipsc",
    "exosome",
    "regeneration",
    "regenerative medicine",
    "восстановление",
    "движение",
    "чувствительность",
    "нейрореабилитация",
    "реабилитация",
    "клиническое испытание",
    "клинические испытания",
    "клинических испытаний",
    "нейростимуляция",
    "электростимуляция",
    "эпидуральная стимуляция",
    "нейроинтерфейс",
    "имплант",
    "устройство",
    "аппарат",
    "робот",
    "экзоскелет",
    "стволовые клетки",
    "стволовых клеток",
    "стволовыми клетками",
    "клеточная терапия",
    "клеточной терапии",
    "клеточная трансплантация",
    "клеточную трансплантацию",
    "мезенхимальные",
    "нейральные стволовые",
    "экзосомы",
    "регенерация",
    "регенеративная медицина",
    "матриселф",
    "нейромат",
]

EXCLUDED_TERMS = [
    "pillow",
    "cushion",
    "mattress",
    "seat cushion",
    "bedding",
    "accessory",
    "accessories",
    "wheelchair",
    "mobility scooter",
    "charity",
    "fundraiser",
    "donation",
    "inspirational",
    "motivation",
    "awareness",
    "disability benefits",
    "social security",
    "lawsuit",
    "settlement",
    "sports story",
    "wellness",
    "fitness tips",
    "подушка",
    "матрас",
    "аксессуар",
    "коляска",
    "благотворительность",
    "сбор средств",
    "мотивационная история",
    "социальная новость",
    "пособие",
    "льготы",
]

EXCLUSION_OVERRIDES = [
    "exoskeleton",
    "robotic wheelchair",
    "brain-computer interface",
    "neurostimulation",
    "implant",
    "экзоскелет",
    "нейроинтерфейс",
    "нейростимуляция",
    "имплант",
]


def _text(finding: Finding) -> str:
    return f"{finding.title} {finding.summary} {' '.join(finding.tags)}".lower()


def is_relevant(finding: Finding) -> bool:
    text = _text(finding)
    has_sci_context = any(term in text for term in SCI_TERMS)
    has_recovery_tech = any(term in text for term in RECOVERY_TECH_TERMS)
    has_exclusion = any(term in text for term in EXCLUDED_TERMS)
    has_override = any(term in text for term in EXCLUSION_OVERRIDES)

    if has_exclusion and not has_override:
        return False

    return has_sci_context and has_recovery_tech


def filter_relevant(findings: list[Finding]) -> list[Finding]:
    return [finding for finding in findings if is_relevant(finding)]
