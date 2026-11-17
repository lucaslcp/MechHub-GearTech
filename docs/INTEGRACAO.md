# Integração GearTech → MechCalc

Integração obrigatória do enunciado: *"GearTech → MechCalc: compartilhar esforços e parâmetros de transmissão para análises mecânicas"*.

## Regra seguida

> As integrações devem utilizar serviços Python e modelos de dados compartilhados, sem acesso direto às tabelas privadas de outros módulos.

| Camada | Arquivo | Quem usa |
|---|---|---|
| Contrato (formato dos dados) | `mechhub/shared/contracts.py` → `TransmissionLoad` | GearTech e MechCalc |
| Tabela compartilhada | `mechhub/shared/models.py` → `shared_transmission_load` | só o serviço |
| Serviço | `mechhub/shared/integration.py` | GearTech publica, MechCalc lê |
| Tabelas privadas do GearTech | `gt_transmission_set`, `gt_stage`, `gt_result_snapshot`, `gt_quick_calculation` | só o GearTech |

O MechCalc **nunca** importa `mechhub.modules.m03_geartech`. Ele só chama:

```python
from mechhub.shared import integration

loads = integration.list_transmission_loads(organization_id)   # lista de TransmissionLoad
load = integration.get_transmission_load(organization_id, load_id)
```

## Fluxo

```
GearTech (detalhe do conjunto)
   │  botão "Enviar ao MechCalc"
   ▼
services.publish_to_mechcalc(ts)
   │  monta 1 TransmissionLoad por eixo: n, T, P, Ft, Fr, Fa
   ▼
shared.integration.publish_transmission_loads(...)
   │  valida (valores positivos, um conjunto por vez)
   │  substitui a publicação anterior do mesmo conjunto
   ▼
tabela shared_transmission_load
   ▲
   │  shared.integration.list_transmission_loads(org)
MechCalc → verificação do eixo à torção: τ = 16T/(πd³)
```

## Dados enviados por eixo

| Campo | Significado |
|---|---|
| `source_ref` | identificador do conjunto (`geartech:set:<id>`) |
| `set_name`, `shaft_index`, `shaft_label` | qual conjunto e qual eixo |
| `speed_rpm`, `torque_nm`, `power_kw` | condição de operação do eixo |
| `tangential_force_n`, `radial_force_n`, `axial_force_n` | maior esforço entre os engrenamentos montados nesse eixo |

## Sincronização

- **Editar** um conjunto já publicado republica os esforços automaticamente.
- **Excluir** um conjunto retira os esforços do MechCalc.
- Cada organização só vê os próprios esforços (multiempresa do SaaS).

## Testes

`tests/test_integration.py` cobre: um registro por eixo, valores iguais aos do cálculo, republicação sem duplicar, retirada na exclusão, isolamento entre organizações, rejeição de dados inválidos e o cálculo de torção no MechCalc com o torque recebido.
