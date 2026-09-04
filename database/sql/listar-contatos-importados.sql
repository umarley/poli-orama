SELECT p.nome_completo,
       CASE WHEN p.sexo = 'M' THEN 'Masculino' ELSE 'Feminino' END AS sexo,
       pce.valor AS email,
       pct.valor AS telefone,
       pcw.valor AS whatsapp
  FROM cadastro.pessoa p
  JOIN etl.fonte_dado f ON f.id = p.fonte_dado_id
  LEFT JOIN cadastro.pessoa_contato pce
         ON p.id = pce.pessoa_id AND pce.tipo_contato = 'email'
  LEFT JOIN cadastro.pessoa_contato pct
         ON p.id = pct.pessoa_id AND pct.tipo_contato = 'telefone'
  LEFT JOIN cadastro.pessoa_contato pcw
         ON p.id = pcw.pessoa_id AND pcw.tipo_contato = 'whatsapp'
 WHERE f.nome = 'Filiados PCdoB - Durval'
   AND p.excluido_em IS NULL;
