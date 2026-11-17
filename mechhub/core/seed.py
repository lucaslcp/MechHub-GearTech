"""Dados fictícios para demonstração e testes (executa só se o banco estiver vazio)."""
from werkzeug.datastructures import MultiDict

from ..extensions import db
from .models import Organization, User

DEMO_EMAIL = "demo@mechhub.local"
DEMO_PASSWORD = "mechhub123"

DEMO_SETS = [
    {
        "name": "Redutor de esteira transportadora",
        "application": "Esteira de mineração",
        "description": "Redutor de dois estágios helicoidais acionado por motor de indução de 4 polos.",
        "input_power_kw": "7,5", "input_speed_rpm": "1750",
        "stages": [
            ("engrenagem_helicoidal", "19", "76", "0,98", "3", "", "15", "1º par helicoidal"),
            ("engrenagem_helicoidal", "21", "84", "0,98", "4", "", "15", "2º par helicoidal"),
        ],
    },
    {
        "name": "Betoneira: correia + engrenagens",
        "application": "Betoneira de 400 L",
        "description": "Polias em V seguidas de um par de dentes retos que aciona a cremalheira do tambor.",
        "input_power_kw": "3", "input_speed_rpm": "1720",
        "stages": [
            ("polia_correia", "100", "250", "0,95", "", "", "", "Correia em V"),
            ("engrenagem_reta", "18", "90", "0,98", "2,5", "", "", "Pinhão e coroa"),
        ],
    },
    {
        "name": "Protótipo Fórmula SAE: redução final",
        "application": "Transmissão de protótipo",
        "description": "Redução primária do motor e transmissão final por corrente 520 (passo 15,875 mm).",
        "input_power_kw": "35", "input_speed_rpm": "8500",
        "stages": [
            ("engrenagem_reta", "30", "54", "0,98", "2,5", "", "", "Redução primária"),
            ("corrente", "12", "38", "0,97", "", "15,875", "", "Corrente 520"),
        ],
    },
    {
        "name": "Motorredutor sem-fim de portão",
        "application": "Portão deslizante",
        "description": "Sem-fim de uma entrada seguido de um par de dentes retos.",
        "input_power_kw": "0,37", "input_speed_rpm": "1700",
        "stages": [
            ("sem_fim", "1", "40", "0,65", "", "", "", "Sem-fim e coroa"),
            ("engrenagem_reta", "14", "28", "0,97", "2", "", "", "Par de saída"),
        ],
    },
]


def demo_form(data: dict) -> MultiDict:
    form = MultiDict({k: v for k, v in data.items() if k != "stages"})
    for stype, z1, z2, eta, module, pitch, helix, label in data["stages"]:
        form.add("stage_type", stype)
        form.add("driver", z1)
        form.add("driven", z2)
        form.add("efficiency", eta)
        form.add("module_mm", module)
        form.add("pitch_mm", pitch)
        form.add("helix_angle_deg", helix)
        form.add("stage_label", label)
    return form


def seed_demo_data() -> None:
    if Organization.query.first() is not None:
        return
    from ..modules.m03_geartech import services

    org = Organization(name="MechHub Demo")
    user = User(name="Usuário Demo", email=DEMO_EMAIL, organization=org, role="admin")
    user.set_password(DEMO_PASSWORD)
    db.session.add_all([org, user])
    db.session.commit()

    created = [services.create_set(org.id, user.id, services.parse_set_form(demo_form(d))) for d in DEMO_SETS]
    services.publish_to_mechcalc(created[0], user.id)
