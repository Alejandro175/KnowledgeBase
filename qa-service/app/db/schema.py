from neo4j import GraphDatabase
from app.core.config import config

driver = GraphDatabase.driver(uri=config.neo4j_uri, auth=(config.neo4j_username, config.neo4j_password))

# ===========================
# SCHEMA DEL DATABASE
# ===========================
neo4j_schema = """
Node properties:
Malware {uri: STRING}
System {uri: STRING}
Attacker {uri: STRING}
Indicator {uri: STRING}
IPAddress {uri: STRING}
EmailAddress {uri: STRING}
File {uri: STRING}
Software {uri: STRING}
URL {uri: STRING}
Hash {uri: STRING}
AttackPattern {uri: STRING}
Location {uri: STRING}
Region {uri: STRING}
Country {uri: STRING}
Organization {uri: STRING}
Report {uri: STRING}
Characteristic {uri: STRING}
Category {uri: STRING}
Capability {uri: STRING}
Information {uri: STRING}
Protocols {uri: STRING}

Relationships:
(Malware)-[:attackOrg]->(Organization)
(Malware)-[:controledBy]->(System)
(Malware)-[:executes]->(AttackPattern)
(Malware)-[:hasAuthor]->(Attacker)
(Malware)-[:hasCharacteristic]->(Characteristic)
(Malware)-[:hasLocation]->(Location)
(Malware)-[:isIndicatedBy]->(Indicator)
(Malware)-[:isIndicatedByAddress]->(IPAddress)
(Malware)-[:isIndicatedByEmail]->(EmailAddress)
(Malware)-[:isIndicatedByFile]->(File)
(Malware)-[:isIndicatedByHash]->(Hash)
(Malware)-[:isIndicatedByUrl]->(URL)
(Malware)-[:isMember]->(Category)
(Malware)-[:isRelatedTo]->(Category)
(Malware)-[:mentionedIn]->(Report)
(Malware)-[:mentionedWith]->(Malware)
(Malware)-[:target]->(Observable)
(Malware)-[:targetInformation]->(Observable)
(Malware)-[:targetSoftware]->(Observable)
(Malware)-[:targetSystems]->(Observable)

Notes:
- Each node has a property 'uri'.
- Return columns must be: subject, predicate, object.
- Use WHERE node.uri ENDS WITH "local-name" to refer to a specific node.
"""

# ===========================
# ESEMPI PER IL MODELLO
# ===========================
examples = [
    "USER INPUT: 'Quali sono tutti gli indicatori del malware Cloud Atlas?' "
    "QUERY: MATCH (mal:Malware { uri: 'http://www.semanticweb.org/mwonto/cloud-atlas'})-[:isIndicatedBy]->(m) "
    "RETURN mal.uri AS subject, 'isIndicatedBy' AS predicate, m.uri AS object",

    "USER INPUT: 'Quali Malware sono relazionati con RedOctober?' "
    "QUERY: MATCH (mal:Malware { uri: 'http://www.semanticweb.org/mwonto/redoctober'})-[r]->(m:Malware) "
    "RETURN mal.uri AS subject, type(r) AS predicate, m.uri AS object",

    "USER INPUT: 'Quali sono le similitudini fra RedOctober e Cloud Atlas?' "
    "QUERY: MATCH (mal1:Malware {uri: 'http://www.semanticweb.org/mwonto/redoctober'})-[r]-(common) "
    "MATCH (mal2:Malware {uri: 'http://www.semanticweb.org/mwonto/cloud-atlas'})-[r2]-(common) "
    "WHERE type(r) = type(r2) "
    "RETURN mal1.uri + ' AND ' + mal2.uri AS subject, type(r) AS predicate, common.uri AS object"
]