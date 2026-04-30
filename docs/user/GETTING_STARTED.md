# Primeiros Passos com Tarifas de Energia Brasil

Este guia irá ajudá-lo a instalar e configurar a integração Tarifas de Energia Brasil para o Home Assistant.

## Pré-requisitos

- Home Assistant 2025.7.0 ou mais recente
- HACS (Home Assistant Community Store) instalado
- Conectividade com a internet para acessar sites das concessionárias

## Instalação

### Via HACS (Recomendado)

1. Abra o HACS na sua instância do Home Assistant
2. Vá para "Integrações"
3. Clique nos três pontos no canto superior direito
4. Selecione "Repositórios Personalizados"
5. Adicione a URL deste repositório: `https://github.com/vodikus/ha_tarifas_energia_brasil`
6. Defina a categoria como "Integração"
7. Clique em "Adicionar"
8. Encontre "Tarifas de Energia Brasil" na lista de integrações
9. Clique em "Baixar"
10. Reinicie o Home Assistant

### Instalação Manual

1. Baixe a versão mais recente da [página de lançamentos](https://github.com/vodikus/ha_tarifas_energia_brasil/releases)
2. Extraia a pasta `tarifas_energia_brasil` do arquivo
3. Copie para `custom_components/tarifas_energia_brasil/` no diretório de configuração do Home Assistant
4. Reinicie o Home Assistant

## Configuração Inicial

Após a instalação, adicione a integração:

1. Vá para **Configurações** → **Dispositivos e Serviços**
2. Clique em **"+ Adicionar Integração"**
3. Pesquise por "Tarifas de Energia Brasil"
4. Siga os passos de configuração:

### Passo 1: Seleção da Concessionária

Selecione sua distribuidora de energia:

- **CELESC** (Santa Catarina)
- **CPFL** (São Paulo, Rio Grande do Sul, Paraná)
- Outras (em desenvolvimento)

Clique em **Enviar** para continuar.

### Passo 2: Modalidade Tarifária

Escolha o tipo de tarifa:

- **Convencional**: Tarifa única durante todo o dia
- **Branca**: Tarifa que varia según o horário (ponta, intermediário, fora de ponta)

### Passo 3: Tipo de Fornecimento

Selecione o tipo de ligação:

- **Monofásico**: 30 kWh de disponibilidade
- **Bifásico**: 50 kWh de disponibilidade
- **Trifásico**: 100 kWh de disponibilidade

### Passo 4: Configuração de Impostos

Escolha como configurar os impostos:

- **Automático**: A integração obtém PIS e COFINS automaticamente do site da concessionária
- **Manual**: Você define os percentuais manualmente

### Passo 5: Configuração da Tarifa Branca (se aplicável)

Se escolher Tarifa Branca, configure os horários:

- **Ponta**: Horário de ponta (mais caro)
- **Intermediário 1 e 2**: Horários intermediários
- **Feriados Extras**: Dias que devem ser cobrados como ponta

Clique em **Enviar** para completar a configuração.

## O que é Criado

Após a configuração bem-sucedida, a integração cria:

### Dispositivo

- **Nome**: Nome da concessionária configurada
- **Informações**: Modelo e versão do software
- **Link**: Link para site da concessionária

### Entidades

As seguintes entidades são automaticamente criadas:

#### Sensores Principais

- `sensor.<concessionaria>_tarifa_vigente` - Tarifa atual cobrada (R$/kWh)
- `sensor.<concessionaria>_bandeira_vigente` - Bandeira tarifária atual
- `sensor.<concessionaria>_tarifa_base_aneel` - Tarifa sem impostos
- `sensor.<concessionaria>_api_status` - Status da conexão

#### Sensores de Impostos

- `sensor.<concessionaria>_aliquota_icms` - Percentual do ICMS
- `sensor.<concessionaria>_aliquota_pis` - Percentual do PIS
- `sensor.<concessionaria>_aliquota_cofins` - Percentual do COFINS

#### Sensores de Consumo

- `sensor.<concessionaria>_fatura_estimada_r` - Valor estimado da fatura
- `sensor.<concessionaria>_consumo_minimo_kwh` - Custo mínimo de disponibilidade

#### Sensores de Geração Solar (SCEE)

- `sensor.<concessionaria>_saldo_creditos_kwh` - Créditos em kWh
- `sensor.<concessionaria>_energia_compensada_kwh` - Energia compensada
- `sensor.<concessionaria>_energia_nao_compensada_kwh` - Energia da rede

#### Sensores de Configuração

- `sensor.<concessionaria>_modalidade_tarifaria` - Modalidade configurada
- `sensor.<concessionaria>_ciclo_quebra` - Ciclo de quebra
- `sensor.<concessionaria>_dia_leitura` - Dia de leitura

Encontre todas as entidades em **Configurações** → **Dispositivos e Serviços** → **Tarifas de Energia Brasil** → clique no dispositivo.

## Primeiros Passos

### Cartões no Dashboard

Adicione entidades ao seu dashboard:

1. Vá para seu dashboard
2. Clique em **Editar Dashboard** → **Adicionar Cartão**
3. Escolha o tipo de cartão (ex: "Entidades", "Glance")
4. Selecione entidades de "Tarifas de Energia Brasil"

Exemplo de cartão de entidades:

```yaml
type: entities
title: Tarifas de Energia Brasil
entities:
  - sensor.celesc_tarifa_vigente
  - sensor.celesc_fatura_estimada_r
  - sensor.celesc_bandeira_vigente
```

### Automações

Use a integração em automações:

**Exemplo - Notificar quando a tarifa mudar:**

```yaml
automation:
  - alias: "Notificar mudança de tarifa"
    trigger:
      - trigger: state
        entity_id: sensor.celesc_tarifa_vigente
    action:
      - action: notify.notify
        data:
          message: "Nova tarifa: {{ trigger.to_state.state }} R$/kWh"
```

**Exemplo - Alerta de fatura alta:**

```yaml
automation:
  - alias: "Alerta fatura alta"
    trigger:
      - trigger: numeric_state
        entity_id: sensor.celesc_fatura_estimada_r
        above: 500
    action:
      - action: notify.notify
        data:
          message: "Fatura estimada alta: R$ {{ trigger.to_state.state }}"
```

## Solução de Problemas

### Conexão Falhou

Se a configuração falhar com erros de conexão:

1. Verifique a conexão com a internet
2. Verifique se o site da ANEEL está acessível
3. Certifique-se de que nenhum firewall está bloqueando
4. Verifique os logs detalhados do Home Assistant

### Entidades Não Atualizando

Se as entidades mostram "Indisponível" ou não atualizam:

1. Verifique se a integração está conectada
2. Verifique os logs em **Configurações** → **Sistema** → **Logs**
3. Tente recarregar a integração
4. Verifique a configuração das opções

### Tarifa Branca Não Aplicando

Se a Tarifa Branca não está sendo aplicada corretamente:

1. Verifique os sensores de horário (Ponta, Intermediário)
2. Configure os horários nas **Opções** da integração
3. Adicione feriados extras se necessário

### Logs de Debug

Habilite logs de debug para solucionar problemas:

```yaml
logger:
  default: warning
  logs:
    custom_components.tarifas_energia_brasil: debug
```

Adicione isto ao `configuration.yaml`, reinicie e reproduza o problema. Verifique os logs para informações detalhadas.

## Próximos Passos

- Reporte problemas em [GitHub Issues](https://github.com/vodikus/ha_tarifas_energia_brasil/issues)

## Suporte

Para ajuda e discussão:

- [GitHub Discussions](https://github.com/vodikus/ha_tarifas_energia_brasil/discussions)
- [Fórum da Comunidade Home Assistant Brasil](https://homeassistantbrasil.com.br/t/preco-do-kwh-e-bandeira-tarifaria/12490/52)
