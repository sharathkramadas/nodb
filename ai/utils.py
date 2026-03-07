class AIUtils:

    def __init__(self):
        self.APP_PROFILE = {
            "framework": "Spring Boot",
            "tomcat": "embedded",
            "tomcat_ui": False,
            "aspectj": False,
            "spring_security_mode": "proxy",
            "deployment": "containerized"
        }

        self.model_name = "gpt-oss:20b"
        self.llm = ChatOllama(model=self.model_name, temperature=0)
        self.parser = StrOutputParser()

    def false_positive_promt(self):
        return ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a cybersecurity analyst AI. "
                "Your job is to assess whether a CVE is a false positive for a given system. "
                "Do not assume anything not provided in the asset profile or CVE advisory. "
                "Consider installed version, patches, configuration, exposure, and exploit requirements."
            ),
            (
                "human",
                """
CVE ID: {cve_id}
CVE Advisory: {cve_advisory_json}
Asset Profile: {asset_profile_json}

Return strictly in JSON format:
- is_false_positive: true or false
- reasons: list of strings explaining why this CVE is or is not a false positive
"""
            )
        ])

    def exploitability_condition_prompt(self):
        return ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a vulnerability analyst. "
                "Extract exploitation conditions exactly as stated. "
                "Do not infer. "
                "Return ONLY valid JSON. "
                "Do not include explanations, markdown, comments, or extra text."
            ),
            (
                "human",
                """
CVE Data: {cve_text}
Application Profile: {app_profile}

Return strictly in the following JSON format:

{
  "required_components": [string],
  "exploitable_os": "Linux" | "Windows" | "Both",
  "needs_shell_access": true | false,
  "not_affected_if": [string],
  "vulnerable_via_class_or_method": {
      "is_vulnerable": true | false,
      "details": string | null
  },
  "vulnerable_via_configuration": {
      "is_vulnerable": true | false,
      "config_file": string | null,
      "usual_path": string | null
  },
  "needs_human_intervention": true | false,
  "needs_public_endpoint": true | false,
  "attack_preconditions": [string]
}
"""
            )
        ])

    def application_profiling_prompt(self):
        return ChatPromptTemplate.from_messages([
            (
                "system",
                "You determine CVE applicability for compliance audits. "
                "Never mark False Positive unless vendor documentation "
                "explicitly states non-affected conditions."
            ),
            (
                "human",
                """
CVE Conditions: {conditions}
Application Profile: {app_profile}

Return:
- Applicable: YES or NO
- Reason (audit-safe)
- Confidence: High / Medium / Low
"""
            )
        ])

    def analyze_cve_exploitability(self, cve_id):
        cve_text = self.fetch_cve(cve_id)

        condition_prompt = self.exploitability_condition_prompt()
        exploitability_condition_chain = condition_prompt | self.llm | self.parser

        conditions = exploitability_condition_chain.invoke({
            "cve_text": cve_text,
            "app_profile": json.dumps(self.APP_PROFILE, indent=2)
        })

        # app_prompt = self.application_profiling_prompt()
        # app_chain = app_prompt | self.llm | self.parser
        # decision = app_chain.invoke({
        #     "conditions": conditions,
        # })

        print(conditions)

    def false_positive_analysis(self, cve_id):
        formatted_prompt = self.false_positive_promt()
        analysis_chain = formatted_prompt | self.llm | self.parser

        decision = analysis_chain.invoke({
            "cve_id": cve_id,
            "cve_advisory_json": self.fetch_cve(cve_id),
            "asset_profile_json": json.dumps({})
        })

        print(decision)

    def fetch_cve(self, cve_id):
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"

        response = requests.get(url, timeout=15)
        response.raise_for_status()

        return json.dumps(response.json(), indent=2)
