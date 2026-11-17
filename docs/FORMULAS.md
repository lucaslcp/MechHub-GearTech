# GearTech — fórmulas e exemplo resolvido

Todas as fórmulas estão em `mechhub/modules/m03_geartech/calculations.py`.

## Unidades

| Grandeza | Símbolo | Unidade |
|---|---|---|
| Potência | P | kW |
| Rotação | n | rpm |
| Velocidade angular | ω | rad/s |
| Torque | T | N·m |
| Diâmetros, módulo, passo | d, m, p | mm |
| Forças | Ft, Fr, Fa | N |
| Velocidade periférica | v | m/s |

## Funcionalidade 2 — relação de transmissão

| Situação | Fórmula | Função |
|---|---|---|
| Engrenagens / corrente | i = Z₂ / Z₁ | `transmission_ratio` |
| Polias e correia | i = d₂ / d₁ | `transmission_ratio` |
| Sem-fim | i = Z_coroa / nº de entradas | `transmission_ratio` |
| Estágios em série | i_total = i₁ · i₂ · … · iₖ | `total_ratio` (NumPy `np.prod`) |

i > 1 → **redutor** (sai mais devagar e com mais torque). i < 1 → **multiplicador**.

## Funcionalidade 3 — rotações

- n₂ = n₁ / i  (`output_speed`)
- ω = 2·π·n / 60  (`angular_speed`)

## Funcionalidade 4 — torque

- T = P / ω → T [N·m] = P [kW] · 1000 / ω  (`torque_from_power`)
  - forma prática: T ≈ 9549 · P / n
- T₂ = T₁ · i · η  (`output_torque`)

## Funcionalidade 5 — potência

- P = T · ω / 1000  (`power_from_torque`)
- P₂ = P₁ · η  (`output_power`); a perda P₁ − P₂ vira calor.
- η_total = η₁ · η₂ · … · ηₖ

Rendimentos típicos usados quando o campo fica vazio: engrenagens 0,98; corrente 0,97; correia 0,95; sem-fim 0,70.

## Geometria e esforços (enviados ao MechCalc)

- Diâmetro primitivo: d = m · Z / cos β (β = 0 em dentes retos) — `pitch_diameter`
- Roda de corrente: d = p / sen(180°/Z) — `sprocket_pitch_diameter`
- Força tangencial: Ft = 2·T / d (d em metros) — `tangential_force`
- Força radial: Fr = Ft · tan α / cos β, com α = 20° — `radial_force`
- Força axial (helicoidal): Fa = Ft · tan β — `axial_force`
- Velocidade periférica: v = π · d · n / 60000 — `peripheral_speed`
- Nº mínimo de dentes sem interferência: Z_min = 2 / sen²α ≈ 17 (× cos³β na helicoidal)

## Funcionalidade 6 — simulação de vários estágios

`simulate_transmission` percorre os estágios do motor até a saída. O eixo k é a saída do estágio k e a entrada do estágio k+1:

```
para cada estágio k:
    i  = Z2 / Z1
    n  = n / i
    P  = P · η
    T  = T · i · η        (é o mesmo que P·1000/ω no eixo novo)
    sentido: engrenagens externas invertem; correia e corrente mantêm
```

`operating_sweep` repete a conta para vários pontos (rotação ou potência do motor variando) usando vetores NumPy.

### Exemplo: redutor de esteira (dados de demonstração)

Motor de 7,5 kW a 1750 rpm, dois pares helicoidais (19/76 e 21/84), η = 0,98 cada.

| Passo | Conta | Resultado |
|---|---|---|
| Torque do motor | 7,5·1000 / (2π·1750/60) | 40,93 N·m |
| Estágio 1 | i₁ = 76/19 | 4,00 |
| Eixo 1 | n = 1750/4; T = 40,93·4·0,98 | 437,5 rpm; 160,43 N·m |
| Estágio 2 | i₂ = 84/21 | 4,00 |
| Eixo de saída | n = 437,5/4; T = 160,43·4·0,98 | 109,4 rpm; 628,9 N·m |
| Totais | i = 16; η = 0,98² | η = 96,04 %; P saída = 7,203 kW |

Conferência: P = T·ω = 628,9 · (2π·109,375/60) / 1000 = 7,203 kW ✔

## MechCalc (lado que recebe a integração)

- τ = 16·T / (π·d³)  — tensão de cisalhamento máxima num eixo maciço
- d_min = (16·T / (π·τ_adm))^(1/3)
- FS = τ_adm / τ
