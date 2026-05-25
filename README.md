# nubank-gastos

Aplicação fullstack dockerizada para cadastro/login com confirmação por email, linkagem de conta Nubank (mock) e dashboard de gastos.

## Stack

- **Backend:** FastAPI + PostgreSQL + Alembic
- **Frontend:** HTML/CSS/JS (Chart.js), servido por Nginx
- **Infra:** Docker Compose

## Funcionalidades

- Cadastro com email/senha
- Confirmação de cadastro por email (Mailhog)
- Login com JWT
- Dashboard com:
  - Gastos do mês por categoria (gráfico de pizza)
  - Gasto anual por mês (gráfico de barras)
  - Card de gasto médio dos últimos 6 meses
  - Tabela de gastos futuros
- Linkagem de conta Nubank (mock, com carga inicial de gastos)
- Página de categorização com alteração manual de categoria
- Cadastro de categoria personalizada
- Banco gerenciado por migrations (Alembic) + seed de categorias padrão

## Como rodar

```bash
docker compose up --build
```

Serviços:

- Frontend: http://localhost:3000
- Backend: http://localhost:8000/docs
- Mailhog: http://localhost:8025

## Fluxo de uso

1. Cadastre um usuário na tela inicial.
2. Abra o Mailhog e copie o link de confirmação recebido por email.
3. Acesse o link para confirmar o cadastro.
4. Faça login.
5. Se a conta Nubank ainda não estiver linkada, clique em **Linkar conta Nubank**.
6. Dashboard e categorização serão preenchidos com dados mockados.
