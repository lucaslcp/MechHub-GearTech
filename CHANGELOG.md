# Notas de versão

## v1.0.0 — 17/11/2026

Primeira entrega do Módulo 3 (GearTech) na plataforma MechHub.

### Plataforma (base comum)
- Login, cadastro com organização e saída; senhas com hash.
- Painel com os 10 módulos, indicadores e atividade recente.
- Serviços compartilhados: gráficos (Plotly), relatórios PDF (ReportLab), histórico e integração.
- Números e datas no padrão brasileiro.

### GearTech
- Cadastro de conjuntos de transmissão com até 10 estágios (engrenagens retas e helicoidais, polias e correia, corrente, sem-fim).
- Cálculo de relação de transmissão, rotação, torque e potência por eixo.
- Diâmetros primitivos, velocidade periférica e forças no dente (Ft, Fr, Fa).
- Simulação estágio a estágio com pré-visualização sem salvar.
- Simulação de operação variando rotação ou potência do motor (NumPy).
- Calculadoras rápidas com histórico salvo.
- Comparação de configurações com destaques e gráficos.
- Relatórios em PDF e exportação CSV.
- Alertas de projeto: interferência, relação alta, velocidade excessiva, sem-fim autotravante.

### Integração GearTech → MechCalc
- Publicação dos esforços por eixo pelo contrato `TransmissionLoad`.
- Versão mínima do MechCalc que verifica eixos à torção com os dados recebidos.
- Republicação automática ao editar e retirada ao excluir.

### Qualidade
- 70 testes automatizados (Pytest).
- Documentação de fórmulas, integração e guia para a defesa.
