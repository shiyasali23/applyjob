"""Skill vocabulary for reading adverts. Matching is whole-word and case-insensitive.

Extend it in workspace/profile/vocab_extra.txt (one term per line) instead of editing this file.
Known false friends are blocked explicitly (lesson: regex once found "Redis" in "Redispatch").
"""
import re
from . import workspace

TERMS = """
Python R SQL NoSQL Scala Java JavaScript TypeScript Go Rust C++ C# Kotlin Swift PHP Ruby MATLAB Julia Bash Shell
pandas NumPy SciPy Polars scikit-learn XGBoost LightGBM CatBoost statsmodels PyTorch TensorFlow Keras JAX Hugging Face
Transformers LangChain LlamaIndex LangGraph OpenAI API LLM LLMs RAG Embeddings Vector Database Fine-Tuning LoRA QLoRA
Prompt Engineering NLP Computer Vision OpenCV YOLO Deep Learning Machine Learning Reinforcement Learning Time Series
Forecasting A/B Testing Statistics Bayesian Causal Inference Recommender Systems MLOps MLflow Kubeflow Weights & Biases
DVC Airflow Dagster Prefect dbt Spark PySpark Databricks Snowflake BigQuery Redshift Synapse Fabric Delta Lake Iceberg
Kafka Flink Beam Hadoop Hive ETL ELT Data Warehouse Data Lake Lakehouse Data Modeling Data Governance Data Quality
PostgreSQL MySQL SQL Server Oracle MongoDB Cassandra Elasticsearch OpenSearch Redis Neo4j DuckDB ClickHouse Parquet
ChromaDB Qdrant Pinecone Weaviate FAISS pgvector
AWS Azure GCP Google Cloud SageMaker Azure ML Vertex AI Bedrock Lambda EC2 S3 ECS EKS AKS GKE Cloud Functions
Docker Kubernetes Helm Terraform Ansible CI/CD GitHub Actions GitLab CI Jenkins Argo CD Git Linux Nginx
FastAPI Flask Django REST GraphQL gRPC Microservices Node.js React Next.js Vue Angular Streamlit Gradio
Power BI Tableau Looker Qlik Excel Grafana Prometheus Superset Metabase
Agile Scrum Jira Confluence SAP Salesforce
""".split()
# multi-word terms (the split above breaks them): listed whole
MULTI = ["Hugging Face", "Vector Database", "Prompt Engineering", "Computer Vision", "Deep Learning", "Machine Learning",
         "Reinforcement Learning", "Time Series", "A/B Testing", "Causal Inference", "Recommender Systems", "Weights & Biases",
         "Delta Lake", "Data Warehouse", "Data Lake", "Data Modeling", "Data Governance", "Data Quality", "SQL Server",
         "Google Cloud", "Azure ML", "Vertex AI", "Cloud Functions", "GitHub Actions", "GitLab CI", "Argo CD", "Power BI",
         "OpenAI API", "Fine-Tuning", "Generative AI", "Large Language Models", "Data Engineering", "Data Science",
         "Feature Engineering", "Model Deployment", "Model Monitoring", "Data Pipelines", "Unit Testing", "pytest"]
# pieces of multi-word terms that are NOT skills on their own (SQL, Azure, Spark stay: they are)
FRAGMENTS = {"Hugging", "Face", "Vector", "Database", "Prompt", "Engineering", "Computer", "Vision", "Deep", "Learning",
             "Machine", "Reinforcement", "Time", "Series", "A/B", "Testing", "Causal", "Inference", "Recommender", "Systems",
             "Weights", "&", "Biases", "Delta", "Lake", "Data", "Warehouse", "Modeling", "Governance", "Quality", "Server",
             "Google", "Cloud", "ML", "Vertex", "AI", "Functions", "GitHub", "Actions", "GitLab", "CI", "Argo", "CD",
             "Power", "BI", "OpenAI", "API"}
FALSE_FRIENDS = {"redis": r"redispatch", "go": r"\bgo\b(?!\s*(lang|programming|developer|engineer))", "r": r".",
                 "rest": r"\brest\b(?!\s*(api|ful|services))", "excel": r"excellen", "spark": r"sparkass",
                 "lambda": r"lambda\s*(calculus)", "beam": r"beamer", "scala": r"skala"}
# methods/fields, not tools: a bullet may name them without the role's stack listing them
CONCEPTS = {c.lower() for c in ["Machine Learning", "Deep Learning", "NLP", "Computer Vision", "Statistics", "Bayesian",
            "Time Series", "Forecasting", "A/B Testing", "Causal Inference", "Recommender Systems", "Reinforcement Learning",
            "ETL", "ELT", "Data Warehouse", "Data Lake", "Lakehouse", "Data Modeling", "Data Governance", "Data Quality",
            "Data Engineering", "Data Science", "Feature Engineering", "Model Deployment", "Model Monitoring", "Data Pipelines",
            "Microservices", "REST", "Agile", "Scrum", "Generative AI", "LLM", "LLMs", "Large Language Models", "RAG",
            "Embeddings", "Fine-Tuning", "Prompt Engineering", "MLOps", "CI/CD", "Unit Testing", "NoSQL", "Vector Database"]}
SINGLE_AMBIGUOUS = {"go", "r", "rest", "excel", "beam", "c"}   # only counted when the advert context is clearly technical


def all_terms():
    words = [t for t in TERMS if t not in FRAGMENTS] + MULTI
    p = workspace.path("profile", "vocab_extra.txt")
    if p.exists():
        words += [l.strip() for l in p.read_text().splitlines() if l.strip() and not l.startswith("#")]
    seen, out = set(), []
    for w in words:
        if w.lower() not in seen: seen.add(w.lower()); out.append(w)
    return out


def rx(term):
    return re.compile(r"(?<![\w+#./-])" + re.escape(term) + r"(?![\w+#-])", re.I)


def find_terms(text, extra=()):
    """Terms present in text, in order of first appearance."""
    hits = []
    for t in list(all_terms()) + list(extra):
        k = t.lower()
        if k in SINGLE_AMBIGUOUS and k not in {"go", "r"}:
            continue
        if k in ("go", "r"):
            if not re.search(r"\b%s\b\s*(\(|,|/|programming|language|lang|developer)|(python|scala|java|sql)\s*(,|/|und|and|or|oder)\s*%s\b" % (k, k), text, re.I):
                continue
        m = rx(t).search(text)
        if not m: continue
        ff = FALSE_FRIENDS.get(k)
        if ff and k not in ("go", "r", "rest") and re.search(ff, text[max(0, m.start() - 2):m.end() + 12], re.I):
            continue
        if k == "rest" and not re.search(r"\brest\s*(api|ful|services|interface)", text, re.I):
            continue
        hits.append((m.start(), t))
    out, seen = [], set()
    for _, t in sorted(hits):
        if t.lower() not in seen: seen.add(t.lower()); out.append(t)
    return out
