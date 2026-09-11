"""Command-Line Interface (CLI) and entry point for Geotechnical Risk Analytics."""

import argparse
import sys
import os
import uvicorn
from src.config.settings import settings
from src.data.terrain_generator import GeotechnicalDataGenerator
from src.models.classifier import GeotechnicalRiskClassifier
from src.visualization.map_renderer import GeotechnicalMapRenderer
from src.domain.models import RiskLevel


def run_pipeline():
    """Execute end-to-end analytical pipeline and generate cartographic output."""
    print("================================================================================")
    print(" GEOTECHNICAL RISK ANALYTICS - PIPELINE DE MONITORAMENTO DE ENCOSTAS")
    print("================================================================================")
    print(f"Area de Estudo: Serra do Mar / Regiao Serrana (Lat: {settings.center_latitude}, Lon: {settings.center_longitude})")
    print("Iniciando geracao e avaliacao de setores de encosta sob cenario pluviometrico critico...")

    data_gen = GeotechnicalDataGenerator()
    classifier = GeotechnicalRiskClassifier()
    map_renderer = GeotechnicalMapRenderer()

    # 1. Generate monitored points
    points = data_gen.generate_monitored_points(n_points=40, storm_scenario=True)
    print(f"[OK] {len(points)} setores de encosta georreferenciados gerados com sucesso.\n")

    # 2. Evaluate each point
    evaluated = [classifier.evaluate_point(p) for p in points]

    # 3. Aggregate metrics
    low = sum(1 for p in evaluated if p.combined_risk_level == RiskLevel.LOW)
    med = sum(1 for p in evaluated if p.combined_risk_level == RiskLevel.MEDIUM)
    high = sum(1 for p in evaluated if p.combined_risk_level == RiskLevel.HIGH)
    crit = sum(1 for p in evaluated if p.combined_risk_level == RiskLevel.CRITICAL)

    avg_fs = sum(p.factor_of_safety for p in evaluated) / len(evaluated)

    print("--------------------------------------------------------------------------------")
    print(" RESUMO DA AVALIACAO GEOTECNICA MULTICRITERIO")
    print("--------------------------------------------------------------------------------")
    print(f"Total de Setores Monitorados:       {len(evaluated)}")
    print(f"Fator de Seguranca Medio (FS):       {avg_fs:.2f}")
    print(f"Setores em Risco Critico (FS < 1.0): {crit} ({crit/len(evaluated)*100:.1f}%)")
    print(f"Setores em Alto Risco:               {high} ({high/len(evaluated)*100:.1f}%)")
    print(f"Setores em Medio Risco:              {med} ({med/len(evaluated)*100:.1f}%)")
    print(f"Setores Estaveis (Baixo Risco):      {low} ({low/len(evaluated)*100:.1f}%)")
    print("--------------------------------------------------------------------------------\n")

    # 4. Display sample critical hotspots
    hotspots = [p for p in evaluated if p.combined_risk_level == RiskLevel.CRITICAL][:5]
    if hotspots:
        print("AMOSTRA DE SETORES CRITICOS PARA ACAO IMEDIATA DA DEFESA CIVIL:")
        for idx, h in enumerate(hotspots, 1):
            print(f" [{idx}] Coordenadas: ({h.latitude:.5f}, {h.longitude:.5f}) | "
                  f"FS: {h.factor_of_safety:.2f} | AHP: {h.ahp_susceptibility_score:.3f} | "
                  f"Prob. Falha: {h.ml_failure_probability*100:.1f}% | Alerta: {h.rainfall_alert_level.value}")
            if h.recommendations:
                print(f"     Acao: {h.recommendations[0]}")
        print("")

    # 5. Generate interactive map
    os.makedirs("output", exist_ok=True)
    map_path = "output/geotechnical_risk_map.html"
    map_renderer.render_map(evaluated, output_filepath=map_path)
    print(f"[OK] Mapa interativo multicamadas gerado: {os.path.abspath(map_path)}")

    # 6. Check AHP consistency
    ahp_report = classifier.ahp_engine.get_consistency_report()
    print(f"[OK] Validacao AHP Saaty: CR = {ahp_report.consistency_ratio:.4f} (Consistente: {ahp_report.is_consistent})")
    print("================================================================================")
    print(" Pipeline concluido com sucesso.")
    print("================================================================================")


def serve_api(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Start uvicorn server for the FastAPI application."""
    print(f"Iniciando API Geotechnical Risk Analytics em http://{host}:{port}")
    print(f"Documentacao interativa OpenAPI disponivel em http://{host}:{port}/docs")
    uvicorn.run("src.api.server:app", host=host, port=port, reload=reload)


def run_tests():
    """Execute pytest test suite."""
    import pytest
    print("Executando testes automatizados do projeto...")
    exit_code = pytest.main(["-v", "tests"])
    sys.exit(exit_code)


def main():
    parser = argparse.ArgumentParser(
        description="Geotechnical Risk Analytics - Motor de Analise de Estabilidade e Suscetibilidade de Encostas"
    )
    parser.add_argument("--run-pipeline", action="store_true", help="Executar pipeline completo e gerar mapa")
    parser.add_argument("--serve-api", action="store_true", help="Iniciar servidor FastAPI")
    parser.add_argument("--run-tests", action="store_true", help="Executar suite de testes unitarios")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host para a API REST")
    parser.add_argument("--port", type=int, default=8000, help="Porta para a API REST")
    parser.add_argument("--reload", action="store_true", help="Modo reload para desenvolvimento da API")

    args = parser.parse_args()

    if args.run_pipeline:
        run_pipeline()
    elif args.serve_api:
        serve_api(host=args.host, port=args.port, reload=args.reload)
    elif args.run_tests:
        run_tests()
    else:
        # Default behavior if no flag passed
        run_pipeline()


if __name__ == "__main__":
    main()
