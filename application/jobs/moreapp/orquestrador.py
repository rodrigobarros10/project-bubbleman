import subprocess
import logging
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
PIPELINE_STAGES = [
    'landing',
    'bronze',
    'silver',
    'gold',
	'fotos_gold'
]

def run_script(stage_name):
    """
    Encontra e executa o script Python para um determinado estágio.
    Ex: Para 'bronze', procura por '/bronze/bronze.py'
    """
    script_name = f"{stage_name}.py"
    script_path = os.path.join(stage_name, script_name)

    if not os.path.exists(script_path):
        logging.error(f"Script não encontrado em '{script_path}'. Pulando estágio '{stage_name}'.")
        return False

    logging.info(f"--- Iniciando estágio: {stage_name.upper()} ---")
    logging.info(f"Executando script: {script_path}")

    try:

        result = subprocess.run(
            [sys.executable, script_path],
            check=True,
            capture_output=True,
            text=True
        )

        logging.info(f"Saída de '{script_name}':\n{result.stdout}")
        logging.info(f"--- Estágio {stage_name.upper()} concluído com sucesso! ---")
        return True
    except subprocess.CalledProcessError as e:

        logging.error(f"Erro ao executar o estágio {stage_name.upper()}!")
        logging.error(f"Script '{script_path}' retornou o código de erro {e.returncode}.")
        logging.error(f"Erro (stderr):\n{e.stderr}")
        return False
    except Exception as e:
        logging.error(f"Um erro inesperado ocorreu no estágio {stage_name.upper()}: {e}")
        return False

def main():
    """
    Função principal que executa todos os estágios da pipeline em ordem.
    """
    logging.info(">>> Iniciando a orquestração da pipeline de dados <<<")

    for stage in PIPELINE_STAGES:
        success = run_script(stage)
        if not success:
            logging.critical(">>> A pipeline foi interrompida devido a um erro. <<<")
            break

    logging.info(">>> Orquestração da pipeline finalizada. <<<")

if __name__ == "__main__":
    main()
