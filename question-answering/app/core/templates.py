from neo4j_graphrag.generation import RagTemplate

class CustomRagTemplate(RagTemplate):
    DEFAULT_SYSTEM_INSTRUCTIONS = """
    As an AI Assistant your role is to support a cybersecurity analyst in assessing potential malware-related threats. Provide actionable insights and practical guidance based on the information available in the context.
    Your primary Goal is Enhance the analyst’s situational awareness by delivering concise, relevant, and context-aware intelligence.
    
    Instructions:
    - Ignore the fields subj_confi and obj_confi in the context.
    - Keep your answers clear, concise, and directly useful to the analyst.
    - Respond only based on the information provided in the context.
    - Do not simply list data points.
    """

    DEFAULT_TEMPLATE = """Context:
    {context}

    Examples:
    {examples}

    Question:
    {query_text}

    Answer:
    """
    EXPECTED_INPUTS = ["context", "query_text", "examples"]

# ===========================
# SCHEMA DEL DATABASE
# ===========================
neo4j_schema = """
Node properties:
Malware {uri: STRING, confidence: float}
System {uri: STRING, confidence: float}
Attacker {uri: STRING, confidence: float}
Indicator {uri: STRING, confidence: float}
IPAddress {uri: STRING, confidence: float}
EmailAddress {uri: STRING, confidence: float}
File {uri: STRING, confidence: float}
Software {uri: STRING, confidence: float}
URL {uri: STRING, confidence: float}
Hash {uri: STRING, confidence: float}
AttackPattern {uri: STRING, confidence: float}
Location {uri: STRING, confidence: float}
Region {uri: STRING, confidence: float}
Country {uri: STRING, confidence: float}
Organization {uri: STRING, confidence: float}
Report {uri: STRING, confidence: float}
Characteristic {uri: STRING, confidence: float}
Category {uri: STRING, confidence: float}
Capability {uri: STRING, confidence: float}
Information {uri: STRING, confidence: float}
Protocols {uri: STRING, confidence: float}
Asset {uri: STRING, confidence: float}
Computer {uri: STRING, confidence: float}
Network {uri: STRING, confidence: float}
BusinessUnit {uri: STRING, confidence: float}

Relationships:
(Malware)-[:attackOrg]->(Organization)
(Malware)-[:controlledBy]->(System)
(Malware)-[:executes]->(AttackPattern)
(Malware)-[:hasAuthor]->(Attacker)
(Malware)-[:hasCharacteristic]->(Characteristic)
(Malware)-[:hasLocation]->(Location, Country, Region)
(Malware)-[:hasOriginCountry]->(Country)
(Malware)-[:hasTargetCountry]->(Country)
(Malware)-[:isIndicatedBy]->(Indicator, IPAddress, EmailAddress, File, Hash, URL)
(Malware)-[:isIndicatedByAddress]->(IPAddress)
(Malware)-[:isIndicatedByEmail]->(EmailAddress)
(Malware)-[:isIndicatedByFile]->(File)
(Malware)-[:isIndicatedByHash]->(Hash)
(Malware)-[:isIndicatedByUrl]->(URL)
(Malware)-[:isMember]->(Category)
(Malware)-[:isRelatedTo]->(Category)
(Malware)-[:mentionedIn]->(Report)
(Malware)-[:mentionedWith]->(Malware)
(Malware)-[:targets]->(Observable, Information, Software, System)
(Malware)-[:targetsInformation]->(Information)
(Malware)-[:targetsSoftware]->(Software))
(Malware)-[:targetsSystems]->(System)
(Computer)-[:uses]->(Software, System, information)
(Computer, Network)-[:operatesIn]->(BusinessUnit)
(Network)-[:connectedTo]->(IPAddress)

Notes:
- Each node has a property 'uri' e 'confidence'.
- Return columns must be: subject, sub_confidence, predicate, object, obj_confidence.
- Use WHERE node.uri ENDS WITH "local-name" to refer to a specific node.
"""

# ===========================
# ESEMPI PER IL MODELLO
# ===========================
examples = [
    "USER INPUT: 'What are all the indicators of the Cloud Atlas malware?' "
    """QUERY: MATCH (mal:Malware) WHERE mal.uri ENDS WITH 'cloud-atlas'
    MATCH (mal)-[:isIndicatedBy]->(m)
    RETURN mal.uri AS subject, mal.confidence AS sub_confidence, 'isIndicatedBy' AS predicate, m.uri AS object, m.confidence AS obj_confidence""",

    "USER INPUT: 'What are the software targets by the malware scanbox?' "
    """QUERY: MATCH (mal:Malware) WHERE mal.uri ENDS WITH 'scanbox'
    MATCH (mal)-[:targets]->(m:Software)
    RETURN mal.uri AS subject, mal.confidence AS sub_confidence, type(r) AS predicate, m.uri AS object, m.confidence AS obj_confidence""",

    "USER INPUT: 'What are the files related to the malware Cloud Atlas?' "
    """QUERY: MATCH (mal:Malware) WHERE mal.uri ENDS WITH 'cloud-atlas'
    MATCH (mal)-[:isIndicatedBy]->(m:File)
    RETURN mal.uri AS subject, mal.confidence AS sub_confidence, 'isIndicatedBy' AS predicate, m.uri AS object, m.confidence AS obj_confidence""",

    "USER INPUT: 'Which malware are related to RedOctober?' "
    """QUERY: MATCH (mal:Malware) WHERE mal.uri ENDS WITH 'redoctober'
    MATCH (mal)-[r]->(m:Malware)
    RETURN mal.uri AS subject, mal.confidence AS sub_confidence, type(r) AS predicate, m.uri AS object, m.confidence AS obj_confidence""",

    "USER INPUT: 'Which countries are related to the origin of RedOctober?' "
    """QUERY: MATCH (mal:Malware) WHERE mal.uri ENDS WITH 'redoctober'
    MATCH (mal)-[r:hasOriginCountry]->(m:Country)
    RETURN mal.uri AS subject, mal.confidence AS sub_confidence, type(r) AS predicate, m.uri AS object, m.confidence AS obj_confidence""",

    "USER INPUT: 'What are the similarities between RedOctober and Cloud Atlas?' "
    """QUERY: MATCH (mal1:Malware) WHERE mal1.uri ENDS WITH 'redoctober'
    MATCH (mal2:Malware) WHERE mal2.uri ENDS WITH 'cloud-atlas'
    MATCH (mal1)-[r]-(common) 
    MATCH (mal2)-[r2]-(common) 
    WHERE type(r) = type(r2) 
    RETURN mal1.uri AS subject, mal1.confidence AS sub_confidence, type(r) AS predicate, common.uri AS object, common.confidence AS obj_confidence
    UNION
    MATCH (mal1:Malware) WHERE mal1.uri ENDS WITH 'redoctober'
    MATCH (mal2:Malware) WHERE mal2.uri ENDS WITH 'cloud-atlas'
    MATCH (mal1)-[r]-(common)
    MATCH (mal2)-[r2]-(common)
    WHERE type(r) = type(r2)
    RETURN mal2.uri AS subject, mal2.confidence AS sub_confidence, type(r2) AS predicate, common.uri AS object, common.confidence AS obj_confidence""",

    "USER INPUT: 'Which computers can be targeted by malware Scanbox?' "
    """QUERY: MATCH (mal:Malware)-[r1:targets]-(entity) WHERE mal.uri ENDS WITH 'scanbox'
    WITH mal, r1, entity
    RETURN mal.uri AS Subject, mal.confidence AS sub_confidence, type(r1) AS predicate, entity.uri AS Object, entity.confidence AS obj_confidence
    UNION ALL
    MATCH (as:Computer)-[r2]-(entity)
    RETURN as.uri AS Subject, as.confidence AS sub_confidence, type(r2) AS predicate, entity.uri AS Object, entity.confidence AS obj_confidence"""
]