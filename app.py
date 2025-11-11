# KODE BERSIH - SALIN DARI SINI

import gradio as gr
import yaml
import json
import os
from typing import Dict, List, Any
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import tempfile

class MentalHealthScreeningApp:
    def __init__(self):
        self.current_lang = "id"
        self.instruments = {}
        self.scoring_configs = {}
        self.i18n = {}
        self.load_configs()
        
    def load_configs(self):
        instruments_dir = "config/instruments"
        scoring_dir = "config/scoring"
        i18n_dir = "config/i18n"
        
        os.makedirs(instruments_dir, exist_ok=True)
        os.makedirs(scoring_dir, exist_ok=True)
        os.makedirs(i18n_dir, exist_ok=True)
        
        if os.path.exists(instruments_dir):
            for filename in os.listdir(instruments_dir):
                if filename.endswith('.yaml'):
                    try:
                        with open(f"{instruments_dir}/{filename}", 'r', encoding='utf-8') as f:
                            config = yaml.safe_load(f)
                            if config and 'id' in config:
                                self.instruments[config['id']] = config
                    except Exception as e:
                        print(f"Warning: Could not load {filename}: {e}")
        
        if os.path.exists(scoring_dir):
            for filename in os.listdir(scoring_dir):
                if filename.endswith('.yaml'):
                    try:
                        with open(f"{scoring_dir}/{filename}", 'r', encoding='utf-8') as f:
                            config = yaml.safe_load(f)
                            if config:
                                self.scoring_configs.update(config)
                    except Exception as e:
                        print(f"Warning: Could not load {filename}: {e}")
        
        if os.path.exists(i18n_dir):
            for filename in os.listdir(i18n_dir):
                if filename.endswith('.json'):
                    try:
                        lang = filename.split('.')[0]
                        with open(f"{i18n_dir}/{filename}", 'r', encoding='utf-8') as f:
                            self.i18n[lang] = json.load(f)
                    except Exception as e:
                        print(f"Warning: Could not load {filename}: {e}")
    
    def calculate_score(self, instrument_id: str, responses: Dict[str, int]) -> Dict[str, Any]:
        instrument = self.instruments.get(instrument_id, {})
        scoring = instrument.get('scoring', {})
        
        if scoring.get('type') == 'sum':
            total = sum(responses.get(item, 0) for item in scoring.get('items', []))
            return {'total': total, 'max_score': scoring.get('max_score', 0)}
        
        elif scoring.get('type') == 'sum_by_category':
            results = {}
            for category, config in scoring.get('categories', {}).items():
                category_score = sum(responses.get(item, 0) for item in config.get('items', []))
                if 'multiplier' in config:
                    category_score *= config['multiplier']
                results[category] = {
                    'score': category_score,
                    'max_score': config.get('max_score', 0)
                }
            return results
        
        return {}
    
    def get_interpretation(self, instrument_id: str, score: Any) -> Dict[str, Any]:
        instrument = self.instruments.get(instrument_id, {})
        interpretation = instrument.get('interpretation', [])
        
        if isinstance(score, dict) and 'total' in score:
            total_score = score['total']
            for band in interpretation:
                if isinstance(band, dict) and 'range' in band:
                    if band['range'][0] <= total_score <= band['range'][1]:
                        return band
        
        elif isinstance(score, dict):
            results = {}
            for category, cat_score in score.items():
                if category in interpretation:
                    for band in interpretation[category]:
                        if isinstance(band, dict) and 'range' in band:
                            if band['range'][0] <= cat_score['score'] <= band['range'][1]:
                                results[category] = band
                                break
            return results
        
        return {}
    
    def create_quick_screening(self):
        if 'phq2' not in self.instruments:
            gr.Markdown("⚠️ Konfigurasi PHQ-2 tidak ditemukan!")
            return
            
        instrument = self.instruments['phq2']
        gr.Markdown(f"## {instrument['title']['id']}")
        gr.Markdown(f"*{instrument['description']['id']}*")
        gr.Markdown(f"**{instrument['timeframe']['id']}**")
        
        item_ids = []
        inputs = []
        for item in instrument.get('items', []):
            item_ids.append(item['id'])
            inputs.append(gr.Radio(
                choices=[(opt['label']['id'], opt['value']) for opt in item.get('options', [])],
                label=item['text']['id']
            ))
        
        submit_btn = gr.Button("Kirim Jawaban", variant="primary")
        result_output = gr.HTML()
        
        def process_quick_screening(*values):
            if not all(v is not None for v in values):
                return "<p style='color: #e74c3c;'>⚠️ Jawab semua pertanyaan terlebih dahulu!</p>"
            
            responses_dict = dict(zip(item_ids, values))
            score = self.calculate_score('phq2', responses_dict)
            interpretation = self.get_interpretation('phq2', score)
            
            if not interpretation:
                return "<p style='color: #e74c3c;'>⚠️ Error dalam interpretasi hasil!</p>"
            
            html = f"""
                <div style='padding: 20px; background-color: #f8f9fa; border-radius: 8px; border-left: 4px solid #4CAF50;'>
                    <h3 style='color: #2c3e50; margin-top: 0;'>Hasil PHQ-2</h3>
                    <p style='font-size: 18px;'><strong>Skor Total:</strong> <span style='color: #e74c3c;'>{score['total']}/{score['max_score']}</span></p>
                    <p style='font-size: 16px;'><strong>Interpretasi:</strong> <span style='color: #3498db;'>{interpretation['label']['id']}</span></p>
                    <p style='font-size: 14px; color: #34495e;'>{interpretation['description']['id']}</p>
            """
            
            if score['total'] >= 3:
                html += """
                    <div style='background-color: #ffebee; border: 1px solid #ef5350; border-radius: 8px; padding: 15px; margin-top: 15px;'>
                        <h4 style='color: #c62828; margin-top: 0;'>⚠️ Screening Positif</h4>
                        <p style='color: #2c3e50;'>Hasil menunjukkan adanya gejala depresi yang memerlukan evaluasi lebih lanjut.</p>
                        <p style='color: #2c3e50;'><strong>Rekomendasi:</strong> Lanjutkan ke PHQ-9 untuk evaluasi lengkap.</p>
                    </div>
                """
            
            html += "</div>"
            return html
        
        submit_btn.click(process_quick_screening, inputs=inputs, outputs=[result_output])
    
    def create_full_assessment(self):
        """Evaluasi lengkap - FIXED VERSION"""
        gr.Markdown("## 📋 Evaluasi Lengkap")
        
        instrument_choice = gr.Dropdown(
            choices=[
                ("PHQ-9 (Depresi)", "phq9"),
                ("GAD-7 (Kecemasan)", "gad7"),
                ("DASS-21 (Distress)", "dass21"),
                ("CBI (Burnout)", "cbi")
            ],
            label="Pilih instrumen evaluasi",
            value="phq9"
        )
        
        start_btn = gr.Button("Mulai Evaluasi", variant="primary")
        
        # Container untuk form dinamis
        with gr.Column() as form_container:
            dynamic_inputs = []
            item_ids_state = gr.State([])
            current_instrument_state = gr.State("")
        
        submit_btn = gr.Button("📝 Kirim Evaluasi", variant="primary", visible=False)
        results_output = gr.HTML()
        pdf_download = gr.File(label="Download Hasil PDF", visible=False)
        
        def generate_form(instrument_id):
            if not instrument_id or instrument_id not in self.instruments:
                return [], [], "", gr.update(visible=False), "", None
            
            instrument = self.instruments[instrument_id]
            item_ids = []
            components = []
            
            components.append(gr.Markdown(f"### {instrument['title']['id']}"))
            components.append(gr.Markdown(f"<p style='color: #7f8c8d;'>{instrument['description']['id']}</p>"))
            
            for item in instrument.get('items', []):
                item_ids.append(item['id'])
                components.append(gr.Radio(
                    choices=[(opt['label']['id'], opt['value']) for opt in item.get('options', [])],
                    label=item['text']['id']
                ))
            
            components.append(gr.Markdown("<br>"))
            return components, item_ids, instrument_id, gr.update(visible=True), "", None
        
        start_btn.click(
            generate_form,
            inputs=[instrument_choice],
            outputs=[form_container, item_ids_state, current_instrument_state, submit_btn, results_output, pdf_download]
        )
        
        def process_full_assessment(item_ids, current_instrument, *values):
            if not item_ids or not current_instrument:
                return "<p style='color: #e74c3c;'>⚠️ Form belum diisi lengkap!</p>", gr.update(visible=False)
            
            if len(values) < len(item_ids) or not all(v is not None for v in values[:len(item_ids)]):
                return "<p style='color: #e74c3c;'>⚠️ Lengkapi semua pertanyaan terlebih dahulu!</p>", gr.update(visible=False)
            
            responses_dict = dict(zip(item_ids, values[:len(item_ids)]))
            score = self.calculate_score(current_instrument, responses_dict)
            interpretation = self.get_interpretation(current_instrument, score)
            
            if not interpretation:
                return "<p style='color: #e74c3c;'>⚠️ Error dalam interpretasi hasil!</p>", gr.update(visible=False)
            
            pdf_buffer = self.generate_pdf_report(current_instrument, score, interpretation, responses_dict)
            
            html = f"""
                <div style='background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px; padding: 20px; margin-top: 20px;'>
                    <h3 style='color: #155724;'>✅ Evaluasi Berhasil</h3>
                    <h4>{self.instruments[current_instrument]['title']['id']}</h4>
                    <p style='font-size: 20px;'><strong>Skor Total:</strong> <span style='color: #d32f2f;'>{score['total']}/{score['max_score']}</span></p>
                    <p style='font-size: 16px;'><strong>Interpretasi:</strong> <span style='color: #388e3c;'>{interpretation['label']['id']}</span></p>
                    <p style='color: #155724;'>{interpretation['description']['id']}</p>
                </div>
            """
            return html, gr.update(value=pdf_buffer, visible=True)
        
        # Bind submit button
        submit_btn.click(
            process_full_assessment,
            inputs=[item_ids_state, current_instrument_state],
            outputs=[results_output, pdf_download]
        )
    
    def generate_pdf_report(self, instrument_id: str, score: Dict, interpretation: Dict, responses: Dict) -> str:
        """Generate PDF report"""
        instrument = self.instruments.get(instrument_id, {})
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as tmp_file:
            with PdfPages(tmp_file) as pdf:
                # Page 1
                fig, ax = plt.subplots(figsize=(8.27, 11.69))
                ax.axis('off')
                
                title_text = instrument.get('title', {}).get('id', 'Laporan')
                ax.text(0.5, 0.95, f"Laporan Hasil {title_text}", 
                       fontsize=24, fontweight='bold', ha='center', va='top', transform=ax.transAxes, color='#2c3e50')
                ax.text(0.5, 0.90, f"Tanggal: {datetime.now().strftime('%d %B %Y')}", 
                       fontsize=12, ha='center', va='top', transform=ax.transAxes, color='#7f8c8d')
                ax.text(0.1, 0.80, "Ringkasan Hasil", fontsize=18, fontweight='bold', color='#2c3e50', transform=ax.transAxes)
                ax.text(0.1, 0.75, f"Skor Total: {score.get('total', 0)}/{score.get('max_score', 0)}", 
                       fontsize=16, color='#e74c3c', fontweight='bold', transform=ax.transAxes)
                
                if isinstance(interpretation, dict):
                    ax.text(0.1, 0.70, f"Interpretasi: {interpretation.get('label', {}).get('id', 'N/A')}", 
                           fontsize=16, color='#3498db', transform=ax.transAxes)
                    ax.text(0.1, 0.65, f"Deskripsi: {interpretation.get('description', {}).get('id', 'N/A')}", 
                           fontsize=14, color='#34495e', wrap=True, transform=ax.transAxes)
                
                ax.add_patch(plt.Rectangle((0.05, 0.55), 0.9, 0.25, fill=False, edgecolor='#3498db', linewidth=2, transform=ax.transAxes))
                ax.text(0.5, 0.05, "⚠️ Platform ini untuk tujuan edukatif dan skrining awal saja", 
                       fontsize=10, ha='center', va='bottom', transform=ax.transAxes, color='#7f8c8d', style='italic')
                
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)
                
                # Page 2
                fig, ax = plt.subplots(figsize=(8.27, 11.69))
                ax.axis('off')
                ax.text(0.5, 0.95, "Detail Jawaban", fontsize=20, fontweight='bold', ha='center', va='top', transform=ax.transAxes, color='#2c3e50')
                
                y_pos = 0.90
                for item_id, response in responses.items():
                    item_text = ""
                    for item in instrument.get('items', []):
                        if item['id'] == item_id:
                            item_text = item['text']['id']
                            break
                    
                    if y_pos < 0.1:
                        pdf.savefig(fig, bbox_inches='tight')
                        plt.close(fig)
                        fig, ax = plt.subplots(figsize=(8.27, 11.69))
                        ax.axis('off')
                        y_pos = 0.95
                    
                    ax.text(0.1, y_pos, f"• {item_text}", fontsize=12, color='#34495e', transform=ax.transAxes)
                    ax.text(0.7, y_pos, f"Jawaban: {response}", fontsize=12, color='#e74c3c', fontweight='bold', transform=ax.transAxes)
                    y_pos -= 0.03
                
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)
            
            return tmp_file.name
    
    def create_results_interface(self):
        gr.Markdown("## 📊 Hasil dan Interpretasi Multi-Standar")
        
        with gr.Row():
            phq9_score = gr.Number(label="PHQ-9 Score (0-27)", minimum=0, maximum=27, value=0)
            gad7_score = gr.Number(label="GAD-7 Score (0-21)", minimum=0, maximum=21, value=0)
        
        analyze_btn = gr.Button("Analisis", variant="primary")
        results_html = gr.HTML()
        
        def analyze(phq9, gad7):
            html = "<div style='margin-top: 20px;'>"
            
            if phq9 > 0:
                phq9_interp = self.get_interpretation('phq9', {'total': phq9})
                if phq9_interp:
                    html += f"""
                        <div style='background-color: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin: 10px 0; border-radius: 8px;'>
                            <h3 style='color: #1976d2; margin-top: 0;'>PHQ-9 (Depresi)</h3>
                            <p style='font-size: 20px;'><strong>Skor:</strong> <span style='color: #d32f2f;'>{phq9}/27</span></p>
                            <p style='font-size: 16px;'><strong>Kategori:</strong> <span style='color: #388e3c;'>{phq9_interp['label']['id']}</span></p>
                            <p style='color: #455a64;'>{phq9_interp['description']['id']}</p>
                        </div>
                    """
            
            if gad7 > 0:
                gad7_interp = self.get_interpretation('gad7', {'total': gad7})
                if gad7_interp:
                    html += f"""
                        <div style='background-color: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 10px 0; border-radius: 8px;'>
                            <h3 style='color: #f57c00; margin-top: 0;'>GAD-7 (Kecemasan)</h3>
                            <p style='font-size: 20px;'><strong>Skor:</strong> <span style='color: #d32f2f;'>{gad7}/21</span></p>
                            <p style='font-size: 16px;'><strong>Kategori:</strong> <span style='color: #388e3c;'>{gad7_interp['label']['id']}</span></p>
                            <p style='color: #455a64;'>{gad7_interp['description']['id']}</p>
                        </div>
                    """
            
            if phq9 == 0 and gad7 == 0:
                html += "<p style='color: #7f8c8d; font-style: italic;'>Masukkan skor untuk melihat interpretasi.</p>"
            
            html += "</div>"
            return html
        
        analyze_btn.click(analyze, inputs=[phq9_score, gad7_score], outputs=[results_html])
    
    def create_panic_assistant(self):
        gr.Markdown("## 🆘 Asisten Serangan Panik")
        
        with gr.Tabs():
            with gr.Tab("Pernapasan"):
                gr.Markdown("### Teknik Pernapasan")
                breathing_type = gr.Dropdown(
                    choices=[("Pernapasan Kotak (4-4-4-4)", "box"), ("4-7-8 Breathing", "478"), ("Pernapasan Dalam", "deep")],
                    label="Pilih teknik pernapasan", value="box"
                )
                start_breathing = gr.Button("🫁 Mulai Latihan Pernapasan", variant="primary")
                breathing_display = gr.HTML()
                
                def breathing_exercise(breathing_type):
                    exercises = {
                        "box": """
                            <div style='text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; color: white;'>
                                <h2 style='color: white; margin-bottom: 20px;'>🫁 Pernapasan Kotak</h2>
                                <div style='width: 200px; height: 200px; border: 4px solid white; margin: 20px auto; border-radius: 15px; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: bold;'>
                                    Tarik Napas<br>4 detik
                                </div>
                                <div style='text-align: left; max-width: 300px; margin: 20px auto;'>
                                    <p>1. Tarik napas selama 4 detik</p>
                                    <p>2. Tahan napas selama 4 detik</p>
                                    <p>3. Keluarkan napas selama 4 detik</p>
                                    <p>4. Tahan kosong selama 4 detik</p>
                                </div>
                            </div>
                        """,
                        "478": """
                            <div style='text-align: center; padding: 30px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 12px; color: white;'>
                                <h2 style='color: white; margin-bottom: 20px;'>🫁 4-7-8 Breathing</h2>
                                <div style='width: 200px; height: 200px; border: 4px solid white; margin: 20px auto; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: bold; text-align: center;'>
                                    Tarik Napas<br>4 detik
                                </div>
                                <div style='text-align: left; max-width: 300px; margin: 20px auto;'>
                                    <p>1. Tarik napas selama 4 detik</p>
                                    <p>2. Tahan napas selama 7 detik</p>
                                    <p>3. Keluarkan napas selama 8 detik</p>
                                </div>
                            </div>
                        """,
                        "deep": """
                            <div style='text-align: center; padding: 30px; background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); border-radius: 12px; color: white;'>
                                <h2 style='color: white; margin-bottom: 20px;'>🫁 Pernapasan Dalam</h2>
                                <div style='width: 200px; height: 200px; border: 4px solid white; margin: 20px auto; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: bold; text-align: center;'>
                                    Tarik Napas<br>Perlahan
                                </div>
                                <div style='text-align: left; max-width: 300px; margin: 20px auto;'>
                                    <p>1. Tarik napas perlahan melalui hidung</p>
                                    <p>2. Biarkan perut mengembang</p>
                                    <p>3. Keluarkan napas perlahan melalui mulut</p>
                                </div>
                            </div>
                        """
                    }
                    return exercises.get(breathing_type, "")
                
                start_breathing.click(breathing_exercise, inputs=[breathing_type], outputs=[breathing_display])
            
            with gr.Tab("Grounding"):
                gr.Markdown("### Teknik Grounding 5-4-3-2-1")
                start_grounding = gr.Button("🌟 Mulai Grounding", variant="primary")
                grounding_display = gr.HTML()
                
                def grounding_exercise():
                    return """
                        <div style='padding: 20px; background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); border-radius: 12px;'>
                            <h2 style='color: #2c3e50; text-align: center; margin-bottom: 20px;'>🌟 Grounding 5-4-3-2-1</h2>
                            <p style='text-align: center; color: #34495e; font-size: 18px; margin-bottom: 20px;'><strong>Gunakan indera Anda untuk kembali ke saat ini:</strong></p>
                            <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;'>
                                <div style='background: rgba(52, 152, 219, 0.1); padding: 20px; border-radius: 8px; border-left: 4px solid #3498db;'>
                                    <h3 style='color: #2980b9; margin-top: 0;'>👁️ 5 HAL YANG ANDA LIHAT</h3>
                                    <p style='color: #2c3e50;'>Lihat sekeliling dan identifikasi 5 benda</p>
                                </div>
                                <div style='background: rgba(46, 204, 113, 0.1); padding: 20px; border-radius: 8px; border-left: 4px solid #2ecc71;'>
                                    <h3 style='color: #27ae60; margin-top: 0;'>👂 4 HAL YANG ANDA DENGAR</h3>
                                    <p style='color: #2c3e50;'>Dengarkan dan identifikasi 4 suara</p>
                                </div>
                                <div style='background: rgba(155, 89, 182, 0.1); padding: 20px; border-radius: 8px; border-left: 4px solid #9b59b6;'>
                                    <h3 style='color: #8e44ad; margin-top: 0;'>✋ 3 HAL YANG ANDA SENTUH</h3>
                                    <p style='color: #2c3e50;'>Sentuh dan identifikasi 3 tekstur</p>
                                </div>
                                <div style='background: rgba(241, 196, 15, 0.1); padding: 20px; border-radius: 8px; border-left: 4px solid #f1c40f;'>
                                    <h3 style='color: #f39c12; margin-top: 0;'>👃 2 HAL YANG ANDA CIUM</h3>
                                    <p style='color: #2c3e50;'>Cium dan identifikasi 2 bau</p>
                                </div>
                                <div style='background: rgba(230, 126, 34, 0.1); padding: 20px; border-radius: 8px; border-left: 4px solid #e67e22;'>
                                    <h3 style='color: #d35400; margin-top: 0;'>👅 1 HAL YANG ANDA RASA</h3>
                                    <p style='color: #2c3e50;'>Rasakan dan identifikasi 1 rasa</p>
                                </div>
                            </div>
                            <p style='text-align: center; color: #7f8c8d; font-style: italic; margin-top: 20px;'>Lakukan latihan ini perlahan dan fokus pada setiap indera</p>
                        </div>
                    """
                
                start_grounding.click(grounding_exercise, inputs=[], outputs=[grounding_display])
    
    def create_education_interface(self):
        gr.Markdown("## 📚 Edukasi Kesehatan Mental")
        
        with gr.Tabs():
            with gr.Tab("Depresi"):
                gr.Markdown("""
                    <div style='background: linear-gradient(to right, #e3f2fd, #f8f9fa); padding: 20px; border-radius: 10px; border-left: 5px solid #2196f3;'>
                        <h2 style='color: #1976d2; margin-top: 0;'>😔 Depresi</h2>
                        <h3 style='color: #2c3e50;'>Definisi</h3>
                        <p style='font-size: 16px; color: #34495e;'>Depresi adalah gangguan suasana perasaan yang ditandai oleh perasaan sedih yang terus-menerus dan kehilangan minat dalam aktivitas sehari-hari.</p>
                        <h3 style='color: #2c3e50;'>Gejala Umum</h3>
                        <ul style='color: #34495e; font-size: 15px; line-height: 1.6;'>
                            <li>Perasaan sedih, kosong, atau putus asa</li>
                            <li>Kehilangan minat atau kesenangan dalam aktivitas</li>
                            <li>Kelelahan atau kehilangan energi</li>
                            <li>Gangguan tidur (insomnia atau hipersomnia)</li>
                            <li>Perubahan nafsu makan</li>
                            <li>Kesulitan berkonsentrasi</li>
                            <li>Perasaan tidak berharga atau bersalah</li>
                            <li>Pikiran tentang kematian atau bunuh diri</li>
                        </ul>
                        <h3 style='color: #2c3e50;'>Pengobatan</h3>
                        <p style='font-size: 16px; color: #34495e;'>Terapi psikologis (CBT, IPT, dll.), Obat antidepresan (jika diperlukan), Kombinasi terapi dan obat, Perubahan gaya hidup dan self-care</p>
                    </div>
                """)
            
            with gr.Tab("Kecemasan"):
                gr.Markdown("""
                    <div style='background: linear-gradient(to right, #fff3e0, #f8f9fa); padding: 20px; border-radius: 10px; border-left: 5px solid #ff9800;'>
                        <h2 style='color: #f57c00; margin-top: 0;'>😰 Kecemasan</h2>
                        <h3 style='color: #2c3e50;'>Definisi</h3>
                        <p style='font-size: 16px; color: #34495e;'>Kecemasan adalah respons normal terhadap stres, tetapi dapat menjadi gangguan jika berlebihan, berlangsung lama, dan mengganggu fungsi sehari-hari.</p>
                        <h3 style='color: #2c3e50;'>Strategi Coping</h3>
                        <ul style='color: #34495e; font-size: 15px; line-height: 1.6;'>
                            <li>Teknik relaksasi dan pernapasan</li>
                            <li>Mindfulness dan meditasi</li>
                            <li>Terapi kognitif-perilaku</li>
                            <li>Olahraga teratur</li>
                            <li>Manajemen stres</li>
                        </ul>
                    </div>
                """)
    
    def create_screening_interface(self):
        with gr.Tabs():
            with gr.Tab("Skrining Cepat"):
                self.create_quick_screening()
            
            with gr.Tab("Evaluasi Lengkap"):
                self.create_full_assessment()
    
    def create_interface(self):
        css = """
        .gradio-container { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .header-gradient { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 12px; margin-bottom: 20px; text-align: center; color: white; box-shadow: 0 10px 20px rgba(0,0,0,0.1); }
        .emergency-banner { background: linear-gradient(45deg, #e74c3c, #c0392b); color: white; padding: 20px; border-radius: 12px; text-align: center; margin-top: 30px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .tab-button { font-size: 16px !important; padding: 12px 24px !important; border-radius: 8px !important; transition: all 0.3s ease !important; margin: 0 5px !important; border: none !important; font-weight: 600 !important; }
        .tab-button:not(.selected) { background: #f8f9fa !important; color: #495057 !important; }
        .tab-button.selected { background: linear-gradient(45deg, #3498db, #2980b9) !important; color: white !important; box-shadow: 0 2px 8px rgba(52, 152, 219, 0.4); }
        """
        
        with gr.Blocks(theme=gr.themes.Soft(), css=css, title="Screening Kesehatan Mental") as app:
            gr.HTML("""
                <div class='header-gradient'>
                    <h1 style='font-size: 2.5em; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>🧠 Screening Kesehatan Mental</h1>
                    <p style='font-size: 1.2em; margin: 10px 0;'>Platform Evaluasi Depresi, Kecemasan, dan Burnout</p>
                    <p style='font-size: 0.9em; opacity: 0.9;'>⚠️ Untuk tujuan edukatif dan skrining awal saja</p>
                </div>
            """)
            
            with gr.Tabs():
                with gr.Tab("🏠 Beranda"):
                    self.create_screening_interface()
                
                with gr.Tab("📊 Hasil"):
                    self.create_results_interface()
                
                with gr.Tab("🆘 Asisten Panik"):
                    self.create_panic_assistant()
                
                with gr.Tab("📚 Edukasi"):
                    self.create_education_interface()
            
            gr.HTML("""
                <div class='emergency-banner'>
                    <h3 style='margin-top: 0;'>🚨 Krisis Darurat</h3>
                    <p style='font-size: 1.1em;'><strong>Layanan Darurat: 112 | Lifeline Indonesia: 021-85203010</strong></p>
                </div>
            """)
        
        return app

if __name__ == "__main__":
    app = MentalHealthScreeningApp()
    interface = app.create_interface()
    
    port = int(os.environ.get("PORT", 7860))
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_error=True,
        enable_queue=True,
        max_threads=10
    )
