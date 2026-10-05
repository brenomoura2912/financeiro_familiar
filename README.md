# 🛡️ Gestão Financeira Familiar

Sistema web desenvolvido em **Python / Django**, **PostgreSQL** e **Tailwind CSS** para auditoria, controle orçamentário e prestação de contas transparente de familiares assistidos.

## 🚀 Funcionalidades

- **Controle de Acessos Multinível (RBAC):** Gestor (controle total, gestão de membros e categorias) e Membros (lançamentos e auditoria).
- **Multi-familiar (Multi-tenant):** Gestão isolada de múltiplos familiares via códigos de convite com dupla verificação.
- **Categorias Inteligentes:** Filtro dinâmico em tempo real de despesas e receitas.
- **Edição & Auditoria:** Edição protegida de lançamentos, anexo de comprovantes fiscais (PDF/Imagens) e histórico por comprador.
- **Relatórios & Gráficos:** Exportação do espelho mensal em formato `.csv` (Excel) e gráfico de distribuição de despesas com Chart.js.

## 🛠️ Tecnologias

- Python 3.11+
- Django
- PostgreSQL & psycopg3
- Tailwind CSS
- Chart.js