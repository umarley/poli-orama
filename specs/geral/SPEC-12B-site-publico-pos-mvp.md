# SPEC-12B - Site Público Pós-MVP

Prioridade principal: P2  
Módulo: `site_publico`, `backend_core/api/public`  
Origem: tarefas posteriores à `SITE-032`, movidas da `SPEC-12-site-publico-comercial.md` em 06/07/2026.

## Objetivo

Evoluir o site público após a entrega do escopo comercial MVP, adicionando conteúdo editorial, estudos de caso autorizados e integração com um provedor real de checkout.

## Tarefas

| ID | Prioridade | Área | Tarefa | Critério de aceite |
| --- | --- | --- | --- | --- |
| SITE-033 | P2 | Frontend | Criar blog com Content Collections. | `/blog` e `/blog/[slug]` funcionam. |
| SITE-034 | P2 | Frontend | Criar cases com autorização. | `/cases` e `/cases/[slug]` funcionam quando houver conteúdo. |
| SITE-035 | P2 | Frontend/Backend | Integrar checkout real. | Provedor escolhido redireciona e webhooks são tratados no backend. |

## Dependências

- Definição do provedor de pagamento e credenciais por ambiente.
- Processo editorial e responsáveis pela revisão de conteúdo.
- Autorizações explícitas para publicação de estudos de caso.
- Revisão jurídica dos conteúdos eleitorais e comerciais.
