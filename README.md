# Tarifas de Energia Brasil - Integração para Home Assistant

Esta integração permite consultar e monitorar as tarifas de energia elétrica vigentes no Brasil, incluindo bandeiras tarifárias, diretamente no Home Assistant. Os dados são obtidos da ANEEL e atualizados automaticamente.

## Funcionalidades

- Consulta automática das tarifas de energia e bandeiras tarifárias.
- Sensores para exibir a tarifa vigente e a bandeira atual.
- Atualização diária dos dados.
- Armazenamento local dos dados para histórico.
- Configuração simples via interface do Home Assistant.

## Instalação

### Via HACS
1. Abra o HACS em seu Home Assistant
2. Clique nos três pontos no canto superior direito e selecione *Custom repositories*
4. Selecione o tipo *Integration* no campo *Type* e adicione a URL do repositório: https://github.com/vodikus/ha_tarifas_energia_brasil 
5. Busque por "*Tarifas de Energia Brasil*" e instale a integração
6. Reinicie o Home Assistant

### Instalação Manual
1. Faça o download do repositório como arquivo ZIP e faça a extração em um diretório local.
2. Copie a pasta `tarifas_energia_brasil` para o diretório `custom_components` do seu Home Assistant.
3. Reinicie o Home Assistant.
4. Adicione a integração "Tarifas Energia Brasil" via interface de configurações.

## Configuração

A configuração é feita via UI (Configurações > Integrações > Adicionar integração). Não é necessário editar arquivos YAML manualmente.

## Sensores Criados

- **sensor.tarifa_vigente**: Valor da tarifa vigente (R$/kWh).
- **sensor.bandeira_atual**: Bandeira tarifária atual (Verde, Amarela, Vermelha, etc).

## Atualização dos Dados

Os dados são atualizados automaticamente uma vez por dia. O intervalo pode ser ajustado no código, se necessário.

## Pontos de Atenção

- A integração depende da disponibilidade da API da ANEEL.
- Em caso de falha na atualização, os sensores podem ficar indisponíveis.
- Os valores exibidos são apenas informativos e podem variar conforme a distribuidora.

## Contribuição

Sinta-se à vontade para abrir issues ou pull requests para sugerir melhorias ou reportar problemas.

## Licença

Este projeto está licenciado sob a [GNU General Public License v3.0 (GPL-3.0)](https://www.gnu.org/licenses/gpl-3.0.html).  
Você pode usar, modificar e distribuir este software, desde que qualquer trabalho derivado também seja distribuído sob a mesma licença

## Apoie o Projeto
Se você achou este projeto útil e gostaria de apoiá-lo, pague me um café.