import json

DISCOVERY_SYSTEM_PROMPT = """
Você é um Product Discovery Copilot sênior.

OBJETIVO
Ajudar Product Managers a compreender problemas, reduzir incerteza e tomar decisões baseadas em evidência antes de escrever requisitos.

PRINCÍPIOS
- Discovery antes de solutioning.
- Não aceite automaticamente a solução proposta pelo usuário.
- Diferencie claramente FATO, EVIDÊNCIA, HIPÓTESE, INFERÊNCIA e DECISÃO.
- Nunca invente entrevistas, métricas, feedbacks, usuários ou dados.
- Quando faltar evidência, diga explicitamente "evidência insuficiente".
- Faça perguntas progressivas: no máximo 3 perguntas principais por rodada.
- Procure falsificar hipóteses, não apenas confirmá-las.
- Explore riscos de valor, usabilidade, viabilidade técnica e viabilidade de negócio.
- Use JTBD quando ajudar a entender contexto, motivação e resultado desejado.
- Considere alternativas atuais, inclusive processos manuais.
- Métricas devem estar ligadas a comportamento e resultado.
- Experimentos devem ser os menores possíveis para reduzir a incerteza prioritária.
- Se houver várias hipóteses, identifique a mais arriscada.
- Não transforme toda conversa em backlog.

ESTILO
- Português do Brasil.
- Direto, profissional e fácil de escanear.
- Prefira blocos curtos.
- Quando fizer sentido, use: O que sabemos / O que estamos assumindo / Maior incerteza / Próximo passo.
"""

DISCOVERY_START_PROMPT = """
TÍTULO: {title}

PROBLEMA / OPORTUNIDADE:
{context}

EVIDÊNCIAS INFORMADAS:
{evidence}

Inicie o discovery. Primeiro:
1. Faça uma leitura crítica do problema sem assumir que a solução já é conhecida.
2. Separe o que já é evidência do que é hipótese.
3. Identifique a maior lacuna atual.
4. Faça no máximo 3 perguntas que mais aumentariam nosso entendimento agora.

Não gere PRD ainda.
"""

def transcript(messages):
    return "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)

def build_brief_prompt(messages):
    return f"""
Com base exclusivamente no histórico abaixo, gere um Product Discovery Brief em Markdown.

HISTÓRICO:
{transcript(messages)}

Estrutura:
# Discovery Brief
## 1. Contexto
## 2. Problema
## 3. Usuários / segmentos afetados
## 4. Evidências
## 5. JTBD / resultado desejado
## 6. Hipóteses
## 7. Assumption Map
### Valor
### Usabilidade
### Viabilidade técnica
### Viabilidade de negócio
## 8. Maior incerteza
## 9. Oportunidades / alternativas consideradas
## 10. Experimentos recomendados
## 11. Métricas
## 12. Decisões tomadas
## 13. Questões em aberto
## 14. Próximo passo recomendado

Regras:
- Não invente informação.
- Marque itens sem sustentação como "Hipótese" ou "Evidência insuficiente".
- Não declare como decisão algo que não tenha sido decidido.
- Seja conciso, mas preserve nuances importantes.
"""

def build_prd_prompt(messages):
    return f"""
Com base exclusivamente no histórico abaixo, gere um PRD enxuto em Markdown.

HISTÓRICO:
{transcript(messages)}

IMPORTANTE:
Um PRD só deve consolidar o que já foi suficientemente compreendido no discovery.
Se partes essenciais ainda estiverem incertas, mantenha-as explicitamente como "Em aberto".

Estrutura:
# Product Requirements Document
## 1. Resumo
## 2. Problema
## 3. Objetivo
## 4. Não objetivos
## 5. Usuários / JTBD
## 6. Evidências que sustentam a iniciativa
## 7. Resultado esperado
## 8. Métricas de sucesso
## 9. Escopo
### Incluído
### Fora de escopo
## 10. Requisitos funcionais
## 11. Requisitos não funcionais
## 12. Fluxos / cenários principais
## 13. Edge cases
## 14. Dependências e restrições
## 15. Riscos
## 16. Hipóteses ainda não validadas
## 17. Questões em aberto
## 18. Plano de validação / rollout
## 19. Decision log

Regras:
- Não crie requisitos que não tenham apoio no histórico.
- Diferencie requisitos confirmados de hipóteses.
- Evite detalhamento técnico prematuro.
- Não invente métricas, metas ou prazos.
"""

def build_ost_prompt(messages):
    return f"""
Analise o histórico de discovery abaixo e devolva SOMENTE JSON válido, sem markdown e sem comentários.
Não invente evidências ou decisões. Quando algo for apenas uma possibilidade, trate como hipótese.

HISTÓRICO:
{transcript(messages)}

Formato obrigatório:
{{
  "problem": "problema central em uma frase",
  "opportunities": [
    {{
      "text": "oportunidade/necessidade observada",
      "evidence_level": "forte|moderada|fraca|insuficiente",
      "solutions": [
        {{
          "text": "solução considerada ou hipótese de solução",
          "experiments": ["experimento 1", "experimento 2"]
        }}
      ]
    }}
  ],
  "risks": {{
    "value": "baixo|médio|alto|incerto",
    "usability": "baixo|médio|alto|incerto",
    "feasibility": "baixo|médio|alto|incerto",
    "business": "baixo|médio|alto|incerto"
  }},
  "next_step": "próximo passo de discovery mais útil"
}}

Regras:
- No máximo 4 oportunidades.
- No máximo 3 soluções por oportunidade.
- No máximo 2 experimentos por solução.
- Se não houver solução discutida, use uma lista vazia em solutions.
- Se não houver evidência suficiente para uma oportunidade, marque evidence_level como "insuficiente".
"""


MEETING_ANALYSIS_PROMPT = """
Você analisa transcrições de reuniões de Product Discovery.

Extraia SOMENTE informações sustentadas pela conversa e devolva SOMENTE JSON válido,
sem markdown, no formato:

{
  "title": "título curto e objetivo",
  "problem_opportunity": "problema ou oportunidade consolidada",
  "evidence": [
    {"text": "evidência observável ou relato explicitamente mencionado", "confidence": "alta|média|baixa"}
  ],
  "users_segments": ["..."],
  "hypotheses": ["..."],
  "solutions_mentioned": ["..."],
  "metrics_mentioned": ["..."],
  "decisions": ["..."],
  "open_questions": ["..."],
  "risks": {
    "clinical": ["..."],
    "operational": ["..."],
    "usability": ["..."],
    "security": ["..."],
    "compliance": ["..."],
    "integration": ["..."],
    "performance": ["..."]
  }
}

Regras:
- Não transforme opinião em evidência.
- Não invente métricas, usuários, impactos ou decisões.
- Soluções sugeridas devem ficar em solutions_mentioned, não no problema.
- Dúvidas e inferências devem ficar em hypotheses ou open_questions.
- Não invente impacto clínico.
- Se houver dados pessoais/sensíveis, evite repetir identificadores desnecessários.
"""

def build_meeting_seed(analysis):
    def bullets(items):
        return "\n".join(f"- {x}" for x in (items or [])) or "- Nenhum item identificado"

    evidence = []
    for item in analysis.get("evidence", []) or []:
        if isinstance(item, dict):
            txt = item.get("text", "")
            conf = item.get("confidence", "")
            evidence.append(f"{txt} [confiança: {conf}]".strip())
        else:
            evidence.append(str(item))

    risks = analysis.get("risks", {}) or {}
    risk_lines = []
    for key, values in risks.items():
        for value in values or []:
            risk_lines.append(f"{key}: {value}")

    return f"""
CONTEXTO EXTRAÍDO DE REUNIÃO E REVISADO PELO USUÁRIO

USUÁRIOS / SEGMENTOS:
{bullets(analysis.get("users_segments"))}

EVIDÊNCIAS:
{bullets(evidence)}

HIPÓTESES:
{bullets(analysis.get("hypotheses"))}

SOLUÇÕES MENCIONADAS:
{bullets(analysis.get("solutions_mentioned"))}

MÉTRICAS MENCIONADAS:
{bullets(analysis.get("metrics_mentioned"))}

DECISÕES:
{bullets(analysis.get("decisions"))}

QUESTÕES EM ABERTO:
{bullets(analysis.get("open_questions"))}

RISCOS MENCIONADOS:
{bullets(risk_lines)}

Não trate hipótese ou solução mencionada como evidência.
"""
