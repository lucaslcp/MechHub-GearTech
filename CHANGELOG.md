# Notas de versão

## v1.1.0 — 17/11/2026

Novo visual e acesso rápido.

### Visual
- Nova paleta "Oficina": grafite, cinza aço e laranja segurança como único acento. Gráficos e PDFs usam as mesmas cores.
- Nova fonte (IBM Plex Sans), menu lateral, barra superior e tela de login redesenhados.
- Hierarquia: o torque na saída é o número principal do conjunto; o painel destaca o GearTech e os últimos conjuntos.
- Proximidade: cada alerta de projeto aparece na linha do estágio, com o botão "Corrigir este estágio". No formulário, cada erro aparece embaixo do campo.
- Reconhecimento: cada tipo de estágio tem um ícone próprio, usado em todas as telas.

### Acesso rápido
- Atalho **MechHub** na Área de Trabalho e no Menu Iniciar (`criar_atalho.py`), que liga o servidor sem janela e abre o navegador.
- `parar_mechhub.pyw` para desligar o servidor.
- `iniciar.bat` também funciona quando só o comando `py` está instalado.

### Qualidade
- 72 testes automatizados (2 novos, para os erros e alertas exibidos no lugar certo).

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
