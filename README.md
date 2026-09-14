# Clínica Garde — Sistema de Agendamento

Sistema Full Stack desenvolvido como teste prático para a Garde.

O projeto implementa um fluxo simples e funcional de agendamento de consultas, com validação de dias úteis, feriados, disponibilidade médica e persistência em PostgreSQL.

## Funcionalidades

- Consulta de horários disponíveis
- Agendamento de consultas
- Listagem de consultas
- Bloqueio de sábados, domingos e feriados brasileiros
- Integração com a API pública Nager.Date
- Prevenção de conflitos de horário
- Limite diário de consultas por médico
- Disponibilidade por turno
- Cadastro automático de pacientes durante o agendamento
- Proteção contra múltiplos agendamentos do mesmo paciente com o mesmo médico na mesma data

## Tecnologias

- Python
- FastAPI
- PostgreSQL
- HTML
- CSS
- JavaScript
- Nager.Date API

## Endpoints

```text
GET  /available?date=2026-02-10&doctor_id=1
POST /appointments
GET  /appointments
GET  /doctors
```

## Regras de negócio

- Atendimento das 08:00 às 18:00
- Consultas de 1 hora
- Último horário de início: 17:00
- Sem agendamentos aos finais de semana
- Sem agendamentos em feriados
- Sem conflito de horário para o mesmo médico
- Limite diário configurável por médico
- Disponibilidade por turno
- Um paciente não pode possuir duas consultas ativas com o mesmo médico na mesma data

## API de feriados

Os feriados brasileiros de 2026 são consultados pelo backend através da API pública Nager.Date:

```text
https://date.nager.at/api/v3/PublicHolidays/2026/BR
```

## Banco de dados

PostgreSQL, banco:

```text
bd_clinicas
```

A modelagem foi preparada para evolução do sistema, contemplando médicos, pacientes, operadores, convênios, disponibilidade, agendamentos e auditoria.

## Instalação

Crie o ambiente virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Crie o `.env` a partir do `.env.example` e informe as credenciais do PostgreSQL.

Execute:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8300
```

Acesse:

```text
http://localhost:8300
```

## Demonstração online

```text
https://haiia.com.br/clinicas
```

## Evolução prevista

A estrutura permite evoluir o projeto para:

- área administrativa
- autenticação de operadores
- cadastro e gestão de médicos
- configuração de turnos e limites
- convênios
- cancelamentos
- auditoria
- relatórios
- integração com WhatsApp
- atendimento por voz
- atendimento assistido por Inteligência Artificial

A camada de IA pode interpretar solicitações em linguagem natural, enquanto as regras de agendamento permanecem validadas pelo backend.

## Autor

Harley Mendes Garcia Junior

