# Guia de estudo para a apresentação e defesa individual

A avaliação diz que quem não entende o código não recebe a mesma nota. Use este guia para que **os dois** integrantes saibam explicar qualquer parte.

## Roteiro de demonstração (5 a 7 minutos)

1. `python run.py` → entrar com `demo@mechhub.local` / `mechhub123`.
2. **Painel**: os 10 módulos no menu, GearTech ativo, atividade recente vinda do Histórico compartilhado.
3. **GearTech → Novo conjunto** (funcionalidade 1): motor 5 kW a 1750 rpm, estágio 1 polia 100→200, estágio 2 engrenagem reta 18→72 com módulo 2. Clicar **Simular sem salvar** (funcionalidade 6) e mostrar o caminho da potência. Depois **Salvar**.
4. Na página do conjunto: relação, rotação, torque, potência (2 a 5), alertas de projeto, gráficos e tabela de esforços.
5. **Simular operação**: variar a rotação do motor e mostrar que o torque cai com a rotação (P constante).
6. **Calculadoras**: fazer uma conta de torque e mostrar que ficou salva no histórico.
7. **Comparar** (funcionalidade 7): marcar 3 conjuntos, mostrar destaques, gráficos e baixar o **PDF** (funcionalidade 8).
8. **Integração**: "Enviar ao MechCalc" → abrir o MechCalc → verificar o eixo de saída do redutor de esteira com d = 40 mm e τ_adm = 40 MPa (reprova, pede 43,1 mm); depois com d = 45 mm (aprova).
9. `python -m pytest` → 70 testes passando.

## Onde está cada funcionalidade

| # | Funcionalidade | Cálculo / regra | Tela |
|---|---|---|---|
| 1 | Cadastrar conjuntos | `services.create_set / update_set / delete_set` | `routes.create / edit / delete` |
| 2 | Relação de transmissão | `calculations.transmission_ratio`, `total_ratio` | Calculadoras, detalhe |
| 3 | Rotações | `calculations.output_speed`, `angular_speed` | Calculadoras, detalhe |
| 4 | Torque | `calculations.torque_from_power`, `output_torque` | Calculadoras, detalhe |
| 5 | Potência | `calculations.output_power`, `power_from_torque` | Calculadoras, detalhe |
| 6 | Múltiplos estágios | `calculations.simulate_transmission`, `operating_sweep` | Simular sem salvar, Simular operação |
| 7 | Comparar configurações | `services.compare` (Pandas) | Comparar |
| 8 | Gráficos e relatórios | `services.set_charts`, `set_report_pdf`, `set_csv` | Detalhe, PDF, CSV |
| + | Integração com MechCalc | `services.publish_to_mechcalc`, `shared/integration.py` | Botão "Enviar ao MechCalc" |

## Perguntas prováveis e respostas curtas

**Por que o torque aumenta quando a rotação diminui?**
Porque a potência se conserva (menos as perdas): P = T·ω. Se ω cai 4 vezes, T sobe 4 vezes (vezes η).

**Qual a diferença entre i maior e menor que 1?**
i > 1 reduz a rotação e aumenta o torque (redutor). i < 1 faz o contrário (multiplicador).

**Como se calcula um redutor de vários estágios?**
Multiplicam-se as relações (i_total = Π iₖ) e os rendimentos (η_total = Π ηₖ). O código faz isso estágio por estágio para saber rotação e torque em cada eixo intermediário.

**De onde vem o 9549?**
T = P/ω = P·1000 / (2π·n/60) = (60000/2π)·P/n ≈ 9549·P/n.

**Para que serve o módulo da engrenagem?**
Define o tamanho do dente: d = m·Z. Com o diâmetro calculamos a força no dente Ft = 2T/d, que o MechCalc usa para dimensionar o eixo.

**Por que aparece o alerta de interferência com Z1 < 17?**
Com ângulo de pressão de 20°, pinhões com menos de ~17 dentes têm o pé do dente "comido" pela ferramenta de corte (adelgaçamento). Z_min = 2/sen²(20°) ≈ 17,1.

**Por que o sem-fim tem rendimento baixo?**
Há muito deslizamento entre o parafuso e a coroa; o atrito transforma parte da potência em calor. Com η < 0,5 ele costuma ser autotravante.

**O que acontece se eu digitar letras ou números negativos?**
`services.parse_number` e `calculations.positive` lançam erros com mensagem em português; a tela mostra todas as mensagens e devolve status 400, sem quebrar o sistema. Há testes para isso.

**Como os dados ficam salvos?**
SQLite com SQLAlchemy. Tabelas privadas `gt_*` (conjuntos, estágios, histórico de resultados, cálculos rápidos) e as compartilhadas da plataforma. Cada cadastro/edição grava também um "snapshot" do resultado.

**Como funciona a integração sem acessar as tabelas do outro módulo?**
O GearTech só conhece o contrato `TransmissionLoad` e a função `publish_transmission_loads`. O MechCalc só chama `list_transmission_loads`. Nenhum importa o código do outro.

**Para que servem NumPy e Pandas no módulo?**
NumPy: produto das relações e varredura vetorizada da simulação de operação. Pandas: tabelas de comparação, escolha do melhor por critério (`idxmax/idxmin`) e exportação CSV.

**Como garantem que os cálculos estão certos?**
Testes com valores conhecidos (ex.: 7,5 kW a 1750 rpm → 40,93 N·m) e testes de conservação de energia em todos os eixos (P = T·ω).

## Divisão sugerida para a apresentação

| Integrante | Parte |
|---|---|
| Integrante A | Fórmulas e `calculations.py` (funcionalidades 2 a 6), testes de cálculo |
| Integrante B | Banco, telas, comparação, relatórios e integração (1, 7, 8 e MechCalc) |

Os dois devem conseguir responder às perguntas acima.
