import os
import re
from langchain_openai import ChatOpenAI
from schemas.models import Request

class QueryTranslator():
    def __init__(self):
        self._llm = ChatOpenAI(
            temperature=0,  # Deterministic output for reproducible results
            api_key=os.getenv("OPENAI_API_TOKEN"), # Load API key from environment
            model="gpt-4o-mini" # Use a lightweight GPT-4 variant
        )

    def extract_name(url: str) -> str:
        """
        Extracts the final segment of a URI by removing known namespace prefixes.

        Args:
            url (str): A full URI string.

        Returns:
            str: The simplified name extracted from the URI.
        """
        prefixes = [
            'http://www.example.org/ontologies/soa-ontology/' #CHANGE
            'http://www.w3.org/2002/07/owl#'
            'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
            'http://www.example.com/relations#'
            'http://www.example.com/soa#'
            'http://www.w3.org/XML/1998/namespace'
            'http://www.w3.org/2001/XMLSchema#'
            'http://www.w3.org/2000/01/rdf-schema#'
        ]
        # Return the last segment after removing matching prefixes
        return next((re.split(r'[#/]', url)[-1] for prefix in prefixes if url.startswith(prefix)), url)
    
    def translate_query(self, request: Request):
        """
        Endpoint that receives a natural language question and returns a Cypher query.

        Args:
            request (QueryRequest): JSON payload containing the question.

        Returns:
            dict: A dictionary with the translated Cypher query.
        """
        question = request.question

        """        
            **Relationships:**
            - 'ns1__dependsOn': (Resource) -[:ns1__dependsOn]-> (Resource) 
            - 'ns1__isConnectedTo': (NetworkComponent) -[:ns1__isConnectedTo]-> (NetworkComponent)
        """

        # Prompt template with system instructions and schema/examples
        prompt = [
            {"role": "system", "content": """
            
            You are an AI that translates natural language queries into Cypher queries.  
            Your task is to output only the Cypher query with no additional text.  
            The Cypher query must return triples in subject-predicate-object format or the URIs of the entities involved. When representing subject, predicate and object, represent them with s, p, o, respectively.

            ### Graph Schema
            The knowledge graph consists of the following main entity types and relationships:

            **Entities:**
            - 'ns0__Computer': A generic computing unit used to host services or run virtualized environments.
            - 'ns0__Software': Executable code and applications that enable business logic and service operation.
            - 'ns0__Resource': Abstract component used or managed by services, such as data or compute capacity.
            - 'ns0__VirtualMachine': A virtualized computer instance hosting services.
            - 'ns0__WindowsMachine': Computing resource running a Windows-based operating system. Windows operating environment.
            - 'ns0__NonVirtualizedInstance': A directly deployed service instance on physical or bare-metal hardware.
            - 'ns0__Router': Device that routes traffic between different networks or segments.
            - 'ns0__InternetworkingDevice': A component like routers or gateways that manage inter-network communication.
            - 'ns0__BasedOnLinuxKernel': Operating system variant based on Linux kernel, such as Ubuntu or CentOS.

            **Relationships with add SubClass**
            - 'ns1__dependsOn': (AnalyticsAndMonitoring | BasedOnLinuxKernel | BasedOnNTKernel | BasedOnXNUKernel | ComplexService | ConnectivityDevice | Container | ContainerManager | CoreService | CustomerEngagement | Hardware | Hypervisor | InfrastructureAndPlatform | InstanceLinuxBase | InstanceWindowsBase | InternetworkingDevice | Machine | MultiInstanceService | NetworkComponent | NonVirtualizedInstance | OperativeSystem | OrchestrateService | OrchestratorService | OrderManagemnt | PrivateService | PublicService | Resource | Router | Service | ServiceInstance | ServiceWithOrchestration | ShoppingManagemnt | Software | StatefullService | StatelessService | Switch | UserManagemnt | VirtualMachine | VirtualizedInstance) -[:ns1__dependsOn]-> (AnalyticsAndMonitoring | BasedOnLinuxKernel | BasedOnNTKernel | BasedOnXNUKernel | ComplexService | ConnectivityDevice | Container | ContainerManager | CoreService | CustomerEngagement | Hardware | Hypervisor | InfrastructureAndPlatform | InstanceLinuxBase | InstanceWindowsBase | InternetworkingDevice | Machine | MultiInstanceService | NetworkComponent | NonVirtualizedInstance | OperativeSystem | OrchestrateService | OrchestratorService | OrderManagemnt | PrivateService | PublicService | Resource | Router | Service | ServiceInstance | ServiceWithOrchestration | ShoppingManagemnt | Software | StatefullService | StatelessService | Switch | UserManagemnt | VirtualMachine | VirtualizedInstance)
            - 'ns1__isConnectedTo': (ConnectivityDevice | InternetworkingDevice | NetworkComponent | Router | Switch) -[:ns1__isConnectedTo]-> (ConnectivityDevice | InternetworkingDevice | NetworkComponent | Router | Switch)
            - 'ns1__implements': (InstanceLinuxBase | InstanceWindowsBase | NonVirtualizedInstance | ServiceInstance | VirtualizedInstance) -[:ns1__implements]-> (AnalyticsAndMonitoring | ComplexService | CoreService | CustomerEngagement | InfrastructureAndPlatform | MultiInstanceService | OrchestrateService | OrchestratorService | OrderManagemnt | PrivateService | PublicService | Service | ServiceWithOrchestration | ShoppingManagemnt | StatefullService | StatelessService | UserManagemnt)

            ### Examples:
            
            #### Example 1
            **Natural language:** "What are Machine1, docker222 and container3365?"
            **Cypher Query:**
            MATCH (resource:ns0__Resource)
            WHERE resource.uri ENDS WITH "Machine1" OR
                resource.uri ENDS WITH "docker222" OR
                resource.uri ENDS WITH "container3365"
            UNWIND labels(resource) AS label
            WITH resource, label
            WHERE label STARTS WITH "ns0__"
            RETURN resource.uri AS subject, 'is A' AS predicate, label AS object
            

            #### Example 2
            **Natural language:** "What is a Machine1"
            **Cypher Query:**
            MATCH (resource:ns0__Resource)
            WHERE resource.uri ENDS WITH "Machine1"
            UNWIND labels(resource) AS label
            WITH resource, label
            WHERE label STARTS WITH "ns0__"
            RETURN resource.uri AS subject, 'is A' AS predicate, label AS object

            
            #### Example 3
            **Natural language:** "What are the resources on which the service cartService depends?"
            **Cypher Query:**
            MATCH (service:ns0__Service { uri: "http://www.example.com/soa#cartService" })-[:ns1__dependsOn]->(dependency:ns0__Resource)
            RETURN service.uri AS subject, 'dependsOn' AS predicate, dependency.uri AS object

            
            #### Example 4
            **Natural language:** "How do the services within the system interact with each other?"
            **Cypher Query:**
            MATCH (sourceService:ns0__Service { uri: "http://www.example.com/soa#cartService" })-[rel:ns1__usesService]->(targetService:ns0__Resource)
            RETURN sourceService.uri AS subject, 'usesService' AS predicate, targetService.uri AS object
            UNION
            MATCH (sourceService:ns0__Service { uri: "http://www.example.com/soa#cartService" })-[rel:ns1__usedBy]->(targetService:ns0__Resource)
            RETURN sourceService.uri AS subject, 'usedBy' AS predicate, targetService.uri AS object

            
            #### Example 5
            **Natural language:** "How are the LAN networks structured in terms of machines and switches?"
            **Cypher Query:**
            MATCH (networkDevice2:ns0__ConnectivityDevice)
            MATCH (networkDevice1:ns0__Machine)<-[:ns1__isConnectedTo]-(networkDevice2)-[:ns1__isConnectedTo]->(networkDevice3:ns0__Machine)
            WHERE networkDevice1 <> networkDevice3
            RETURN networkDevice1.uri AS subject, networkDevice2.uri AS predicate, networkDevice3.uri AS object
            
            #### Example 6
            **Natural language:** "What connections exist between the different LAN networks?"
            **Cypher Query:**
            MATCH (networkDevice2:ns0__InternetworkingDevice)
            MATCH (networkDevice1:ns0__ConnectivityDevice)<-[:ns1__isConnectedTo]-(networkDevice2)-[:ns1__isConnectedTo]->(networkDevice3:ns0__ConnectivityDevice)
            WHERE networkDevice1 <> networkDevice3
            RETURN networkDevice1.uri AS subject, networkDevice2.uri AS predicate, networkDevice3.uri AS object

            Ensure that the output strictly follows the Cypher query format and does not include any explanatory text.
            """},
            {"role": "user", "content": f"Question:\n{question}"}
        ]

        # Invoke the language model with the crafted prompt
        response = self._llm.invoke(prompt)
        cypher_query = response.content.strip()

        return {"cypher_query": cypher_query}
