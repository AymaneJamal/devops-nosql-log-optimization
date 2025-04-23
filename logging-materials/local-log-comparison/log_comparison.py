import json
import time
import os
import shutil
import requests
import docker
import random
from datetime import datetime
from pymongo import MongoClient
import mysql.connector
from tabulate import tabulate
import matplotlib.pyplot as plt

# --- CONFIGURATION ---
JENKINS_LOG_PATH = "/Users/aymanejamal/.jenkins/workspace/patient-management-logging-materials/host-logs/logs.json"
LOG_FILE = "../host-logs/logs.json"
LOGSTASH_URL = "http://localhost:9502"
LOG_COUNT = 1000
LOG_LEVELS = ["INFO", "DEBUG", "WARN", "ERROR", "CRITICAL"]
docker_client = docker.from_env()

# --- Envoi des logs simulés à Logstash ---
def send_logs(count):
    for i in range(count):
        level = random.choice(LOG_LEVELS)
        payload = {
            "source": "perf-test",
            "level": level,
            "message": f"log-{i}",
            "container_name": "tester",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        }
        try:
            requests.post(LOGSTASH_URL, json=payload, timeout=1)
        except:
            continue

# --- Attente de la création du fichier logs.json ---
def wait_for_logs_json():
    for _ in range(30):
        if os.path.exists(JENKINS_LOG_PATH) and os.path.getsize(JENKINS_LOG_PATH) > 0:
            return
        time.sleep(1)
    print("❌ logs.json not found")
    exit(1)

# --- Copie du fichier JSON depuis Jenkins vers local ---
def copy_logs_json():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    shutil.copyfile(JENKINS_LOG_PATH, LOG_FILE)

# --- Chargement des logs depuis le fichier JSON ---
def load_logs():
    with open(LOG_FILE, 'r') as f:
        return [json.loads(line) for line in f if line.strip()]

# --- Mesure CPU et RAM pendant une opération ---
def measure_resource_during(container_name, operation_fn):
    container = docker_client.containers.get(container_name)
    stats_gen = container.stats(stream=True)

    next(stats_gen)  # warm-up
    time.sleep(0.1)
    stats_before = json.loads(next(stats_gen))

    t0 = time.time()
    result = operation_fn()
    duration = time.time() - t0

    stats_after = json.loads(next(stats_gen))

    cpu = calculate_cpu_percent(stats_after, stats_before)
    mem_mb = stats_after['memory_stats']['usage'] / (1024 * 1024)

    return result, duration, round(cpu, 2), round(mem_mb, 2)

def calculate_cpu_percent(current, previous):
    try:
        cpu_delta = current['cpu_stats']['cpu_usage']['total_usage'] - previous['cpu_stats']['cpu_usage']['total_usage']
        sys_delta = current['cpu_stats']['system_cpu_usage'] - previous['cpu_stats']['system_cpu_usage']
        if sys_delta > 0:
            percpu = current['cpu_stats']['cpu_usage'].get('percpu_usage', [0])
            num_cores = len(percpu)
            return (cpu_delta / sys_delta) * num_cores * 100
    except:
        pass
    return 0.0

# --- Insertion MongoDB ---
def insert_mongo_fn(logs):
    client = MongoClient("mongodb://admin:password@localhost:27017/?authSource=admin")
    db = client["logging"]
    col = db.logs
    col.delete_many({})
    col.insert_many(logs)
    return len(logs)

# --- Requête MongoDB ---
def query_mongo_fn():
    client = MongoClient("mongodb://admin:password@localhost:27017/?authSource=admin")
    db = client["logging"]
    return len(list(db.logs.find({})))

# --- Insertion MySQL ---
def insert_mysql_fn(logs):
    conn = mysql.connector.connect(
        host="localhost", port=13306, user="loguser",
        password="logpassword", database="logging"
    )
    cur = conn.cursor()
    cur.execute("DELETE FROM logs")
    for log in logs:
        try:
            ts = datetime.strptime(log["timestamp"], "%Y-%m-%dT%H:%M:%S.000Z").strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("INSERT INTO logs (source, message, container_name, timestamp) VALUES (%s, %s, %s, %s)", (
                log.get("source", ""), log.get("message", ""), log.get("container_name", ""), ts
            ))
        except:
            continue
    conn.commit()
    cur.close()
    conn.close()
    return len(logs)

# --- Requête MySQL ---
def query_mysql_fn():
    conn = mysql.connector.connect(
        host="localhost", port=13306, user="loguser",
        password="logpassword", database="logging"
    )
    cur = conn.cursor()
    cur.execute("SELECT * FROM logs")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return len(rows)

# --- Génère les graphiques PNG ---
def generate_charts(results, output_prefix):
    labels = ["MongoDB", "MySQL"]

    # Insert Time
    insert_times = [results["mongo_insert"]["time"], results["mysql_insert"]["time"]]
    plt.bar(labels, insert_times, color=["skyblue", "orange"])
    plt.title("Insert Time (s)")
    plt.ylabel("Seconds")
    plt.savefig(f"{output_prefix}_insert_time.png")
    plt.clf()

    # Query Time
    query_times = [results["mongo_query"]["time"], results["mysql_query"]["time"]]
    plt.bar(labels, query_times, color=["skyblue", "orange"])
    plt.title("Query Time (s)")
    plt.ylabel("Seconds")
    plt.savefig(f"{output_prefix}_query_time.png")
    plt.clf()

    # CPU
    cpu_values = [results["mongo_insert"]["cpu"], results["mysql_insert"]["cpu"],
                  results["mongo_query"]["cpu"], results["mysql_query"]["cpu"]]
    plt.bar(["Mongo Insert", "MySQL Insert", "Mongo Query", "MySQL Query"], cpu_values, color="green")
    plt.title("CPU Usage (%)")
    plt.ylabel("CPU %")
    plt.savefig(f"{output_prefix}_cpu_usage.png")
    plt.clf()

    # Memory
    mem_values = [results["mongo_insert"]["mem"], results["mysql_insert"]["mem"],
                  results["mongo_query"]["mem"], results["mysql_query"]["mem"]]
    plt.bar(["Mongo Insert", "MySQL Insert", "Mongo Query", "MySQL Query"], mem_values, color="purple")
    plt.title("Memory Usage (MB)")
    plt.ylabel("Memory (MB)")
    plt.savefig(f"{output_prefix}_memory_usage.png")
    plt.clf()

# --- Lancement du benchmark complet ---
def run_benchmark():
    print("🚀 Sending logs...")
    send_logs(LOG_COUNT)
    wait_for_logs_json()
    copy_logs_json()
    logs = load_logs()

    print("📥 Inserting...")
    mongo_res, mongo_ins_time, mongo_ins_cpu, mongo_ins_mem = measure_resource_during("mongodb", lambda: insert_mongo_fn(logs))
    mysql_res, mysql_ins_time, mysql_ins_cpu, mysql_ins_mem = measure_resource_during("mysql", lambda: insert_mysql_fn(logs))

    print("🔎 Querying...")
    mongo_qres, mongo_q_time, mongo_q_cpu, mongo_q_mem = measure_resource_during("mongodb", query_mongo_fn)
    mysql_qres, mysql_q_time, mysql_q_cpu, mysql_q_mem = measure_resource_during("mysql", query_mysql_fn)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_path = f"benchmark_results_{timestamp}.txt"

    results = {
        "mongo_insert": {"time": mongo_ins_time, "cpu": mongo_ins_cpu, "mem": mongo_ins_mem},
        "mysql_insert": {"time": mysql_ins_time, "cpu": mysql_ins_cpu, "mem": mysql_ins_mem},
        "mongo_query":  {"time": mongo_q_time, "cpu": mongo_q_cpu, "mem": mongo_q_mem},
        "mysql_query":  {"time": mysql_q_time, "cpu": mysql_q_cpu, "mem": mysql_q_mem},
    }

    with open(output_path, "w") as f:
        f.write("=== INSERTION RESULTS ===\n")
        f.write(tabulate([
            ["MongoDB", mongo_res, f"{mongo_ins_time:.2f}s", f"{mongo_ins_cpu}%", f"{mongo_ins_mem:.2f}MB"],
            ["MySQL", mysql_res, f"{mysql_ins_time:.2f}s", f"{mysql_ins_cpu}%", f"{mysql_ins_mem:.2f}MB"]
        ], headers=["Storage", "Log Count", "Insert Time", "CPU", "Memory"], tablefmt="github"))
        f.write("\n\n=== QUERY RESULTS ===\n")
        f.write(tabulate([
            ["MongoDB", f"{mongo_q_time:.2f}s", f"{mongo_q_cpu}%", f"{mongo_q_mem:.2f}MB"],
            ["MySQL", f"{mysql_q_time:.2f}s", f"{mysql_q_cpu}%", f"{mysql_q_mem:.2f}MB"]
        ], headers=["Storage", "Query Time", "CPU", "Memory"], tablefmt="github"))

    generate_charts(results, f"benchmark_{timestamp}")

    print(f"\n✅ Benchmark complete. Results saved to {output_path} and PNG charts generated.")

if __name__ == "__main__":
    run_benchmark()