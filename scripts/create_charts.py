# scripts/generate_charts.py
"""
Generador de gráficos profesionales para RIOCAJA SMART
Crea gráficos listos para incluir en tesis
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path
import numpy as np

class ChartGenerator:
    def __init__(self):
        self.data_file = Path("tests/reports/ocr_performance_report.json")
        self.output_dir = Path("final_reports/graficos")
        self.output_dir.mkdir(exist_ok=True)
        
        # Configurar estilo profesional
        plt.style.use('default')
        plt.rcParams['font.family'] = 'Arial'
        plt.rcParams['font.size'] = 11
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.alpha'] = 0.3

    def load_data(self):
        """Cargar datos de las pruebas"""
        with open(self.data_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def create_bank_performance_chart(self, data):
        """Gráfico de rendimiento por banco"""
        bank_performance = data['bank_performance']
        
        # Preparar datos
        banks = []
        accuracies = []
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        for bank, accuracy in bank_performance.items():
            bank_name = bank.replace('_', ' ').title()
            if bank_name == "Banco Guayaquil":
                bank_name = "Banco de\nGuayaquil"
            elif bank_name == "Banco Pacifico":
                bank_name = "Banco del\nPacífico"
            elif bank_name == "Banco Internacional":
                bank_name = "Banco\nInternacional"
            
            banks.append(bank_name)
            accuracies.append(accuracy * 100)
        
        # Crear gráfico
        fig, ax = plt.subplots(figsize=(12, 8))
        bars = ax.bar(banks, accuracies, color=colors[:len(banks)], 
                     edgecolor='black', linewidth=1)
        
        # Personalizar
        ax.set_title('Precisión OCR por Entidad Bancaria\nRIOCAJA SMART', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Entidad Bancaria', fontsize=12, fontweight='bold')
        ax.set_ylabel('Precisión (%)', fontsize=12, fontweight='bold')
        ax.set_ylim(70, 90)
        
        # Línea de objetivo (80%)
        ax.axhline(y=80, color='red', linestyle='--', alpha=0.8, 
                  linewidth=2, label='Objetivo mínimo (80%)')
        
        # Valores en las barras
        for bar, accuracy in zip(bars, accuracies):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                   f'{accuracy:.1f}%', ha='center', va='bottom', 
                   fontweight='bold', fontsize=11)
        
        # Leyenda y formato
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=0, ha='center')
        plt.tight_layout()
        
        # Guardar
        chart_file = self.output_dir / "precision_por_banco.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return chart_file

    def create_processing_time_chart(self, data):
        """Gráfico de tiempos de procesamiento"""
        detailed_results = data['detailed_results']
        
        # Preparar datos
        test_names = []
        times = []
        
        for result in detailed_results:
            test_names.append(f"Test {result['test_id']:02d}")
            times.append(result['processing_time'])
        
        # Crear gráfico
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Línea principal
        line = ax.plot(test_names, times, marker='o', linewidth=2, 
                      markersize=8, color='#2E86AB', markerfacecolor='#A23B72')
        
        # Personalizar
        ax.set_title('Tiempo de Procesamiento OCR por Caso de Prueba\nRIOCAJA SMART', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Caso de Prueba', fontsize=12, fontweight='bold')
        ax.set_ylabel('Tiempo (segundos)', fontsize=12, fontweight='bold')
        
        # Línea de objetivo (3.0s)
        ax.axhline(y=3.0, color='red', linestyle='--', alpha=0.8, 
                  linewidth=2, label='Objetivo máximo (3.0s)')
        
        # Promedio
        avg_time = sum(times) / len(times)
        ax.axhline(y=avg_time, color='green', linestyle='-', alpha=0.8, 
                  linewidth=2, label=f'Promedio ({avg_time:.3f}s)')
        
        # Valores en los puntos
        for i, time in enumerate(times):
            ax.annotate(f'{time:.3f}s', (i, time), textcoords="offset points", 
                       xytext=(0,10), ha='center', fontsize=9, fontweight='bold')
        
        # Formato
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Guardar
        chart_file = self.output_dir / "tiempos_procesamiento.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return chart_file

    def create_success_rate_chart(self, data):
        """Gráfico circular de tasa de éxito"""
        summary = data['test_summary']
        
        passed = summary['passed_tests']
        total = summary['total_tests']
        failed = total - passed
        
        # Datos para el gráfico circular
        sizes = [passed, failed] if failed > 0 else [passed]
        labels = ['Aprobados', 'Fallidos'] if failed > 0 else ['Aprobados']
        colors = ['#2E86AB', '#F24236'] if failed > 0 else ['#2E86AB']
        explode = (0.1, 0) if failed > 0 else (0.1,)
        
        # Crear gráfico
        fig, ax = plt.subplots(figsize=(10, 8))
        
        wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, 
                                         autopct='%1.1f%%', startangle=90,
                                         explode=explode, shadow=True,
                                         textprops={'fontsize': 12, 'fontweight': 'bold'})
        
        # Personalizar
        ax.set_title('Tasa de Éxito de Pruebas OCR\nRIOCAJA SMART', 
                    fontsize=16, fontweight='bold', pad=20)
        
        # Estadísticas en el gráfico
        stats_text = f'Total: {total} pruebas\nÉxito: {passed}/{total}\nTasa: {summary["success_rate"]:.1%}'
        ax.text(1.3, 0.5, stats_text, fontsize=12, fontweight='bold',
               bbox=dict(boxstyle="round,pad=0.3", facecolor="lightblue"))
        
        plt.tight_layout()
        
        # Guardar
        chart_file = self.output_dir / "tasa_exito.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return chart_file

    def create_comparison_chart(self, data):
        """Gráfico comparativo: Objetivo vs Obtenido"""
        metrics = [
            ('Precisión OCR', 80, data['test_summary']['average_accuracy'] * 100, '%'),
            ('Tiempo Procesamiento', 3.0, data['test_summary']['average_processing_time'], 's'),
            ('Tasa de Éxito', 95, data['test_summary']['success_rate'] * 100, '%')
        ]
        
        # Preparar datos
        metric_names = [m[0] for m in metrics]
        objectives = [m[1] for m in metrics]
        results = [m[2] for m in metrics]
        
        x = np.arange(len(metric_names))
        width = 0.35
        
        # Crear gráfico
        fig, ax = plt.subplots(figsize=(12, 8))
        
        bars1 = ax.bar(x - width/2, objectives, width, label='Objetivo', 
                      color='lightcoral', alpha=0.7, edgecolor='black')
        bars2 = ax.bar(x + width/2, results, width, label='Obtenido', 
                      color='lightblue', alpha=0.7, edgecolor='black')
        
        # Personalizar
        ax.set_title('Objetivos vs Resultados Obtenidos\nRIOCAJA SMART', 
                    fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Métricas', fontsize=12, fontweight='bold')
        ax.set_ylabel('Valores', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(metric_names)
        ax.legend()
        
        # Valores en las barras
        for bars, values, units in [(bars1, objectives, [m[3] for m in metrics]), 
                                   (bars2, results, [m[3] for m in metrics])]:
            for bar, value, unit in zip(bars, values, units):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                       f'{value:.1f}{unit}' if unit != 's' else f'{value:.3f}{unit}',
                       ha='center', va='bottom', fontweight='bold')
        
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Guardar
        chart_file = self.output_dir / "objetivos_vs_resultados.png"
        plt.savefig(chart_file, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        return chart_file

    def generate_all_charts(self):
        """Generar todos los gráficos"""
        print("📊 Generando gráficos profesionales para RIOCAJA SMART...")
        
        try:
            # Cargar datos
            data = self.load_data()
            
            # Generar gráficos
            charts = []
            
            print("   📈 Creando gráfico de precisión por banco...")
            charts.append(self.create_bank_performance_chart(data))
            
            print("   ⏱️ Creando gráfico de tiempos de procesamiento...")
            charts.append(self.create_processing_time_chart(data))
            
            print("   ✅ Creando gráfico de tasa de éxito...")
            charts.append(self.create_success_rate_chart(data))
            
            print("   📊 Creando gráfico comparativo...")
            charts.append(self.create_comparison_chart(data))
            
            print(f"\n✅ Gráficos generados exitosamente:")
            for chart in charts:
                print(f"   📊 {chart.name}")
            
            print(f"\n📁 Ubicación: {self.output_dir}")
            print(f"🎯 Listos para incluir en tu tesis!")
            
            return charts
            
        except Exception as e:
            print(f"❌ Error generando gráficos: {e}")
            return []

if __name__ == "__main__":
    try:
        # Verificar matplotlib
        import matplotlib
        generator = ChartGenerator()
        generator.generate_all_charts()
    except ImportError:
        print("❌ matplotlib no está instalado")
        print("📦 Instalar con: pip install matplotlib")
        print("🔄 O usar la opción manual con Excel/Google Sheets")