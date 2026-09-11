"""Interactive cartographic visualization engine based on Folium and Leaflet."""

import folium
from folium.plugins import HeatMap, MeasureControl, Fullscreen
from typing import List
from src.domain.schemas import SlopePointEvaluationResponse
from src.domain.models import RiskLevel
from src.config.settings import settings


class GeotechnicalMapRenderer:
    """Renders interactive multi-layer geotechnical hazard maps."""

    COLOR_MAP = {
        RiskLevel.LOW: "#10b981",       # Emerald green
        RiskLevel.MEDIUM: "#eab308",    # Yellow / Amber
        RiskLevel.HIGH: "#f97316",      # Bright Orange
        RiskLevel.CRITICAL: "#ef4444"   # Red
    }

    def __init__(self, center_lat: float = None, center_lon: float = None, zoom_start: int = 12):
        self.center_lat = center_lat or settings.center_latitude
        self.center_lon = center_lon or settings.center_longitude
        self.zoom_start = zoom_start

    def render_map(
        self,
        evaluated_points: List[SlopePointEvaluationResponse],
        output_filepath: str = "output/geotechnical_risk_map.html"
    ) -> folium.Map:
        """Generate interactive Leaflet map with markers, heatmaps and geotechnical popups."""
        m = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=self.zoom_start,
            tiles="OpenStreetMap",
            control_scale=True
        )

        # Alternative base tile layers
        folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery",
            name="Satelite (Esri)"
        ).add_to(m)

        # Feature Groups for Layer Control
        critical_group = folium.FeatureGroup(name="Setores Criticos (FS < 1.0)", show=True)
        high_group = folium.FeatureGroup(name="Setores de Alto Risco (1.0 <= FS < 1.25)", show=True)
        medium_group = folium.FeatureGroup(name="Setores de Medio Risco (1.25 <= FS < 1.5)", show=False)
        low_group = folium.FeatureGroup(name="Setores Estaveis (FS >= 1.5)", show=False)

        heat_data = []

        for p in evaluated_points:
            color = self.COLOR_MAP.get(p.combined_risk_level, "#3b82f6")

            # Heatmap weight proportional to failure probability and inverse of FS
            weight = min(1.0, max(0.1, p.ml_failure_probability + (0.5 if p.factor_of_safety < 1.2 else 0.0)))
            heat_data.append([p.latitude, p.longitude, weight])

            # Popup HTML
            recs_html = "".join(f"<li style='margin-bottom: 3px;'>{r}</li>" for r in p.recommendations[:2])
            popup_html = f"""
            <div style='font-family: Arial, sans-serif; min-width: 240px; font-size: 12px; color: #1e293b;'>
                <div style='background-color: {color}; color: white; padding: 6px 10px; font-weight: bold; border-radius: 4px 4px 0 0;'>
                    RISCO GEOTECNICO: {p.combined_risk_level.value}
                </div>
                <div style='padding: 8px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-top: none;'>
                    <p style='margin: 3px 0;'><strong>Fator de Seguranca (FS):</strong> {p.factor_of_safety:.2f} ({p.stability_status})</p>
                    <p style='margin: 3px 0;'><strong>Indice AHP:</strong> {p.ahp_susceptibility_score:.3f}</p>
                    <p style='margin: 3px 0;'><strong>Probabilidade Falha (ML):</strong> {p.ml_failure_probability * 100:.1f}%</p>
                    <p style='margin: 3px 0;'><strong>Alerta Pluviometrico:</strong> {p.rainfall_alert_level.value}</p>
                    <div style='margin-top: 6px; padding-top: 6px; border-top: 1px dashed #cbd5e1;'>
                        <strong>Recomendacoes:</strong>
                        <ul style='margin: 4px 0; padding-left: 16px;'>{recs_html}</ul>
                    </div>
                </div>
            </div>
            """

            marker = folium.CircleMarker(
                location=[p.latitude, p.longitude],
                radius=8 if p.combined_risk_level == RiskLevel.CRITICAL else 6,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.85,
                weight=2,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"Risco: {p.combined_risk_level.value} | FS: {p.factor_of_safety:.2f}"
            )

            if p.combined_risk_level == RiskLevel.CRITICAL:
                marker.add_to(critical_group)
            elif p.combined_risk_level == RiskLevel.HIGH:
                marker.add_to(high_group)
            elif p.combined_risk_level == RiskLevel.MEDIUM:
                marker.add_to(medium_group)
            else:
                marker.add_to(low_group)

        # Heatmap Layer
        if heat_data:
            heatmap_layer = HeatMap(
                heat_data,
                name="Mapa de Calor de Suscetibilidade",
                min_opacity=0.3,
                radius=25,
                blur=20,
                show=True
            )
            heatmap_layer.add_to(m)

        # Attach feature groups to map
        critical_group.add_to(m)
        high_group.add_to(m)
        medium_group.add_to(m)
        low_group.add_to(m)

        # Controls & Tools
        Fullscreen(position="topright").add_to(m)
        MeasureControl(position="topleft", primary_length_unit="meters").add_to(m)
        folium.LayerControl(position="topright", collapsed=False).add_to(m)

        # Save HTML if requested
        if output_filepath:
            import os
            os.makedirs(os.path.dirname(output_filepath) if os.path.dirname(output_filepath) else ".", exist_ok=True)
            m.save(output_filepath)

        return m
