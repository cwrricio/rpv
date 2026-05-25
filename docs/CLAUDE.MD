A ideia desse projeto é ser um sistema de gestão de pós graduação que:

1. Gerencia professores, programas de pesquisa, projetos, bolsas.

2. Atualiza dados academicos como publicações a partir de API como OpenAlex. Utiliza também de Agentes de IA (agno) para buscar dados na web e conseguir os dados de autores via currículo lattes (forma de webscraping)

3. Gera graficos e relatorios de analise de dados que podem ser exportados para plataformas como sucupira.

Decisões arquiteturais.

1. Banco de dados não relacional. 
2. Cloud scheduler e run para disparar a coleta de produções academicas
3. FAST API e uv para o que não for preciso 
4. Modelo raw e canonical para os dados academicos.


