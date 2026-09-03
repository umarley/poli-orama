select * from tse.resultados_eleicoes re 
inner join "global".municipio m on re.cd_municipio = m.codigo_tse 
inner join "global".zona_eleitoral ze on ze.codigo_municipio_ibge = m.codigo_ibge and ze.numero_zona = re.nr_zona 
inner join "global".secao_eleitoral se on se.numero_secao = re.nr_secao and se.zona_eleitoral_id = ze.id 
where re.nm_votavel in ('FÁBIO TOKARSKI', 'FABIO TOKARSKI')