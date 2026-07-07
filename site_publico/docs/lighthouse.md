# Auditoria Lighthouse do site público

## Metas

| Categoria | Meta |
| --- | ---: |
| Performance | 90 |
| Acessibilidade | 90 |
| Boas práticas | 90 |
| SEO | 95 |

As rotas obrigatórias da auditoria são `/`, `/plataforma`, `/planos`, `/demo` e `/contato`, em viewport mobile e sem extensões de navegador.

## Execução

1. Execute `pnpm build` e `pnpm preview --host 127.0.0.1`.
2. Audite cada rota no Lighthouse, usando navegação privada e a configuração mobile padrão.
3. Registre data, versão do Chrome/Lighthouse e resultados na tabela abaixo.

## Resultado em 06/07/2026

O build, o HTML estático, os metadados e os testes de formulário foram validados. A medição numérica do Lighthouse depende de Chrome compatível no ambiente de CI/desenvolvimento e deve ser registrada antes do deploy.

Pendências conhecidas para a medição:

- a imagem social é SVG; validar a compatibilidade do canal de compartilhamento e gerar PNG se necessário;
- repetir a auditoria com o endpoint de planos em condição normal e indisponível;
- confirmar que o provedor de analytics escolhido não reduz Performance abaixo de 90;
- revisar os textos legais com assessoria jurídica antes da publicação.
