"""Registro dos 10 módulos da plataforma, usado na navegação e no painel.

Cada equipe só precisa mudar `endpoint` quando o seu Blueprint estiver pronto.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleInfo:
    number: int
    key: str
    name: str
    description: str
    icon: str  # nome de ícone do Bootstrap Icons
    endpoint: str | None = None  # rota inicial; None = módulo ainda não entregue
    status: str = "em desenvolvimento"


MODULES: list[ModuleInfo] = [
    ModuleInfo(1, "mechcalc", "MechCalc", "Cálculos de resistência dos materiais", "rulers",
               "mechcalc.index", "integração demo"),
    ModuleInfo(2, "maintcontrol", "MaintControl", "Gestão de manutenção industrial", "tools"),
    ModuleInfo(3, "geartech", "GearTech", "Análise de transmissões mecânicas", "gear-wide-connected",
               "geartech.index", "ativo"),
    ModuleInfo(4, "thermolab", "ThermoLab", "Cálculos e simulações térmicas", "thermometer-half"),
    ModuleInfo(5, "vibrasense", "VibraSense", "Análise de vibrações mecânicas", "activity"),
    ModuleInfo(6, "prodfactory", "ProdFactory", "Planejamento e controle da produção", "building-gear"),
    ModuleInfo(7, "energymech", "EnergyMech", "Análise de consumo energético", "lightning-charge"),
    ModuleInfo(8, "qualitycontrol", "QualityControl", "Controle estatístico da qualidade", "clipboard-data"),
    ModuleInfo(9, "materialselect", "MaterialSelect", "Seleção de materiais de engenharia", "boxes"),
    ModuleInfo(10, "motoranalytics", "MotorAnalytics", "Análise de desempenho de motores", "speedometer2"),
]


def get_module(key: str) -> ModuleInfo | None:
    return next((m for m in MODULES if m.key == key), None)
