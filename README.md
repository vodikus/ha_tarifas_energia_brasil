# Tarifas de Energia Brasil

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
![Project Maintenance][maintenance-shield]

## ✨ Funcionalidades

Integração do Home Assistant para consultar e monitorar tarifas de energia elétrica das concessionárias brasileiras.

- **Consulta automática de tarifas**: Obtém tarifas vigentes da sua concessionária diretamente do site da ANEEL
- **Cálculo de impostos**: Calcula valores com ICMS, PIS e COFINS. Eles podem ser extraídos automaticamente do site das concessionárias (veja as concessionárias suportadas na seção abaixo.) ou informados manualmente.
- **Suporte à Tarifa Branca**: Configuração de horários de ponta e intermediário para tarifas horárias
- **Cálculo de créditos (SCEE)**: Estimativa de economia com energia solar compensada
- **Estimativa de fatura**: Calcula valor estimado da fatura mensal com base no consumo
- **Múltiplas concessionárias**: Suporte a diferentes distribuidoras de energia

### Concessionárias Suportadas

| Concessionária | Scraper Automático    |
| -------------- | --------------------- |
| CELESC (SC)    | ✅ Sim                |
| CPFL           | ✅ Sim                |
| Outras         | 🏗️ Em desenvolvimento |

## 🚀 Instalação e Configuração

### Pré-requisitos

Esta integração requer [HACS](https://hacs.xyz/) (Home Assistant Community Store) instalado.

Clique no botão abaixo para abrir a integração diretamente no HACS:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=jpawlowski&repository=ha_tarifas_energia_brasil&category=integration)

Depois:

1. Clique em "Download" para instalar a integração
2. **Reinicie o Home Assistant** (obrigatório após instalação)

> [!NOTE]
> O redirecionamento do My Home Assistant primeiro levará a uma página inicial. Clique no botão para abrir sua instância do Home Assistant.

<details>
<summary><strong>Instalação Manual (Avançada)</strong></summary>

Se preferir não usar o HACS:

1. Baixe a pasta `custom_components/tarifas_energia_brasil/` deste repositório
2. Copie para o diretório `custom_components/` do seu Home Assistant
3. Reinicie o Home Assistant

</details>

### Adicionar a Integração

**Importante:** Primeiro instale a integração (veja acima) e reinicie o Home Assistant!

#### Opção 1: Configuração Rápida

Clique no botão abaixo para abrir o diálogo de configuração:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=tarifas_energia_brasil)

Siga os passos do assistente:

**Modalidade de Tarifa Convencional**

1. Selecione sua concessionária
   ![Adicionar Integração](/docs/user/images/configuracao-convencional-001.png "Adicionar Integração")
2. Preencha as configurações iniciais:

- Modalidade tarifária convencional
- Tipo de Fornecimento (monofásico, bifásico ou trifásico)
- Entidades de Consumo, Geração e Injeção. **OPCIONAL** - necessário somente se quiser o controle via extensão. Para o controle via painel de Energia, basta configurar na tela.
  ![Configurações Básicas 1](/docs/user/images/configuracao-convencional-002.png "Configurações Básicas 1")

1. Configure os impostos (automático ou manual) e o Ciclo do Cálculo
   ![Configurações Básicas 2](/docs/user/images/configuracao-convencional-003.png "Configurações Básicas 2")
2. Clique em Enviar
3. Caso o **Modo de Extração de Impostos** for manual, será exibido o próximo passo para preenchimento dos dados. Caso contrário, os dados de impostos serão extraídos automaticamente do site da Concessionária.
   ![Configurações Impostos](/docs/user/images/configuracao-imposto-manual-001.png "Configurações Impostos")
4. Escolha o nome do dispositivo e a área em que ele pertence (opcional).
   ![Configurações Básicas 3](/docs/user/images/configuracao-convencional-004.png "Configurações Básicas 3")

É isso! A integração começará a carregar seus dados.

**Modalidade de Tarifa Branca**

1. Selecione sua concessionária
   ![Adicionar Integração](/docs/user/images/configuracao-tarifa-branca-001.png "Adicionar Integração")
2. Preencha as configurações iniciais:

- Modalidade tarifária branca
- Tipo de Fornecimento (monofásico, bifásico ou trifásico)
- Entidades de Consumo, Geração e Injeção. **OPCIONAL** - necessário somente se quiser o controle via extensão. Para o controle via painel de Energia, basta configurar na tela.
  ![Configurações Básicas 1](/docs/user/images/configuracao-tarifa-branca-002.png "Configurações Básicas 1")

1. Configure os impostos (automático ou manual) e o Ciclo do Cálculo
   ![Configurações Básicas 2](/docs/user/images/configuracao-tarifa-branca-003.png "Configurações Básicas 2")
2. Clique em Enviar
3. Configure os dados referente à Tarifa Branca.
   ![Configurações Básicas 2](/docs/user/images/configuracao-tarifa-branca-004.png "Configurações Básicas 2")
4. Clique em Enviar
5. Caso o **Modo de Extração de Impostos** for manual, será exibido o próximo passo para preenchimento dos dados. Caso contrário, os dados de impostos serão extraídos automaticamente do site da Concessionária.
   ![Configurações Impostos](/docs/user/images/configuracao-imposto-manual-001.png "Configurações Impostos")
6. Escolha o nome do dispositivo e a área em que ele pertence (opcional).
   ![Configurações Básicas 3](/docs/user/images/configuracao-tarifa-branca-005.png "Configurações Básicas 3")

É isso! A integração começará a carregar seus dados.

#### Opção 2: Configuração Manual

1. Vá para **Configurações** → **Dispositivos e Serviços**
2. Clique em **"+ Adicionar Integração"**
3. Pesquise por "Tarifas de Energia Brasil"
   ![Adicionar Integração](/docs/user/images/instalacao-001.png "Adicionar Integração")
4. Siga os mesmos passos da Opção 1

### Entidades Criadas

A integração cria várias entidades para monitoramento:

#### Sensores Principais

- **Tarifa Vigente**: Tarifa atual cobrada (R$/kWh)
- **Bandeira Vigente**: Bandeira tarifária atual
- **Tarifa Base ANEEL**: Tarifa sem impostos
- **Alíquotas**: ICMS, PIS, COFINS
- **Estimativa Fatura**: Valor estimado da conta mensal
- **Consumo Mínimo**: Custo de disponibilidade

#### Sensores de Geração Solar (SCEE)

- **Saldo de Créditos**: Créditos em kWh
- **Energia Compensada**: Energia solar compensada
- **Energia Não Compensada**: Energia consumida da rede
- **Auto Consumo**: Consumo próprio estimado
- **Fio B Compensado**: Custo efetivo com distribuição

#### Sensores de Configuração

- **Modalidade Tarifária**: convencional ou branca
- **Ciclo de Quebra**: diário, semanal ou mensal
- **Dia de Leitura**: Dia do mês para reset

Encontre todas as entidades em **Configurações** → **Dispositivos e Serviços** → **Tarifas de Energia Brasil** → clique no dispositivo.

![Adicionar Integração](/docs/user/images/entidades-convencional-001.png "Adicionar Integração")

![Adicionar Integração](/docs/user/images/entidades-convencional-002.png "Adicionar Integração")
![Adicionar Integração](/docs/user/images/entidades-tarifa-branca-001.png "Adicionar Integração")
![Adicionar Integração](/docs/user/images/entidades-tarifa-branca-002.png "Adicionar Integração")

## Opções de Configuração

### Durante a Instalação

| Nome                 | Obrigatório | Descrição                         |
| -------------------- | ----------- | --------------------------------- |
| Concessionária       | Sim         | Sua distribuidora de energia      |
| Modalidade Tarifária | Sim         | convencional ou branca            |
| Tipo de Fornecimento | Sim         | monofásico, bifásico ou trifásico |
| Modo de Impostos     | Sim         | automático ou manual              |
| Alíquota ICMS        | Condicional | Percentual do ICMS (se manual)    |
| Alíquota PIS         | Condicional | Percentual do PIS (se manual)     |
| Alíquota COFINS      | Condicional | Percentual do COFINS (se manual)  |

## Solução de Problemas

### Status da Conexão

Monitore o status da conexão com o sensor **Conexão da API**:

- **Conectado**: Integração recebendo dados normalmente
- **Desconectado**: Falha na conexão ou autenticação
  - Verifique os atributos do sensor para informações de diagnóstico
  - Verifique a conectividade com a internet
  - Verifique se o site da concessionária está acessível

### Logs de Debug

Para habilitar logs de debug, adicione ao seu `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.tarifas_energia_brasil: debug
```

### Problemas Comuns

#### Dados Não Atualizando

Se os dados mostram "Indisponível" ou não atualizam:

1. Verifique se a integração está conectada
2. Verifique se o site da concessionária está acessível
3. Verifique os logs em **Configurações** → **Sistema** → **Logs**
4. Tente recarregar a integração

#### Tarifa Branca Não Aplicando

Se a Tarifa Branca não está sendo aplicada corretamente:

1. Verifique os sensores de horário (Ponta, Intermediário)
2. Configure os horários nos **Configurações** da integração
3. Adicione feriados extras se necessário

## 🤝 Contribuindo

Contribuições são bem-vindas! Abra uma issue ou pull request se tiver sugestões ou melhorias.

---

## [!WARNING] Informações Importantes

> [!NOTE]
> Esta versão ainda está em pre-release, ou seja, ainda existem features que não estão totalmente homologadas. Se encontrar comportamento inesperado, por favor [abra uma issue](../../issues) no GitHub.

---

## 🤖 Desenvolvimento Assistido por IA

> [!NOTE]
> **Aviso de Transparência:** Esta integração foi desenvolvida com assistência de agentes de IA (GitHub Copilot, Claude e outros). Embora o código siga os padrões do Home Assistant Core, código gerado por IA pode não ser revisado ou testado na mesma medida que código escrito manualmente. Ferramentas de IA foram usadas para gerar código boilerplate, implementar recursos padrão (config flow, coordinator, entities), garantir qualidade e segurança de código, e escrever documentação. Se encontrar comportamento inesperado, por favor [abra uma issue](../../issues) no GitHub.

---

## 📄 Licença

Este projeto está licenciado sob a Licença GPL 3 - veja o arquivo [LICENSE](LICENSE) para detalhes.

## Apoie o Projeto

Se você achou este ou outros projetos úteis e gostaria de apoiá-los, há várias maneiras.

[!["Me Paga um Café"](/docs/user/images/me-paga-um-cafe.png "Me Paga um Café")](https://mepagaumcafe.com.br/vodikus/)

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/vodikus)

---

**Feito com ❤️ por [@vodikus][user_profile]**

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/vodikus/ha_tarifas_energia_brasil.svg?style=for-the-badge
[commits]: https://github.com/vodikus/ha_tarifas_energia_brasil/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/vodikus/ha_tarifas_energia_brasil.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40vodikus-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/vodikus/ha_tarifas_energia_brasil.svg?style=for-the-badge
[releases]: https://github.com/vodikus/ha_tarifas_energia_brasil/releases
[user_profile]: https://github.com/jpawlowski
