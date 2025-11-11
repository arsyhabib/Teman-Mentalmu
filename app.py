import gradio as gr
import yaml
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import math

class MentalHealthScreeningApp:
    def __init__(self):
        self.current_lang = "id"
        self.instruments = {}
        self.scoring_configs = {}
        self.i18n = {}
        self.load_configs()
        
    def load_configs(self):
        """Load all YAML configuration files"""
        # Load instruments
        instruments_dir = "config/instruments"
        for filename in os.listdir(instruments_dir):
            if filename.endswith('.yaml'):
                with open(f"{instruments_dir}/{filename}", 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    self.instruments[config['id']] = config
        
        # Load scoring configs
        scoring_dir = "config/scoring"
        for filename in os.listdir(scoring_dir):
            if filename.endswith('.yaml'):
                with open(f"{scoring_dir}/{filename}", 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    self.scoring_configs.update(config)
        
        # Load i18n
        i18n_dir = "config/i18n"
        for filename in os.listdir(i18n_dir):
            if filename.endswith('.json'):
                lang = filename.split('.')[0]
                with open(f"{i18n_dir}/{filename}", 'r', encoding='utf-8') as f:
                    self.i18n[lang] = json.load(f)
    
    def get_text(self, key: str, lang: str = None) -> str:
        """Get translated text by key"""
        if lang is None:
            lang = self.current_lang
        
        keys = key.split('.')
        value = self.i18n.get(lang, self.i18n['id'])
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return key  # Return key if translation not found
        
        return value if isinstance(value, str) else key
    
    def calculate_score(self, instrument_id: str, responses: Dict[str, int]) -> Dict[str, Any]:
        """Calculate score for an instrument"""
        instrument = self.instruments[instrument_id]
        scoring = instrument['scoring']
        
        if scoring['type'] == 'sum':
            total = sum(responses.get(item, 0) for item in scoring['items'])
            return {'total': total, 'max_score': scoring['max_score']}
        
        elif scoring['type'] == 'sum_by_category':
            results = {}
            for category, config in scoring['categories'].items():
                category_score = sum(responses.get(item, 0) for item in config['items'])
                if 'multiplier' in config:
                    category_score *= config['multiplier']
                results[category] = {
                    'score': category_score,
                    'max_score': config['max_score']
                }
            return results
        
        return {}
    
    def get_interpretation(self, instrument_id: str, score: Any) -> Dict[str, Any]:
        """Get interpretation for a score"""
        instrument = self.instruments[instrument_id]
        interpretation = instrument['interpretation']
        
        if isinstance(score, dict) and 'total' in score:
            # Single score interpretation
            total_score = score['total']
            for band in interpretation:
                if band['range'][0] <= total_score <= band['range'][1]:
                    return band
        
        elif isinstance(score, dict):
            # Multi-category interpretation
            results = {}
            for category, cat_score in score.items():
                if category in interpretation:
                    for band in interpretation[category]:
                        if band['range'][0] <= cat_score['score'] <= band['range'][1]:
                            results[category] = band
                            break
            return results
        
        return {}
    
    def check_safety_flags(self, responses: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for safety flags and risk indicators"""
        flags = []
        safety_rules = self.scoring_configs.get('safety', {})
        
        # Check suicide screening
        suicide_screening = safety_rules.get('suicide_screening', {})
        for rule in suicide_screening.get('instruments', []):
            if rule['id'] in responses:
                instrument_responses = responses[rule['id']]
                if isinstance(instrument_responses, dict):
                    item_response = instrument_responses.get(rule['item'], 0)
                    if item_response >= rule['threshold']:
                        flags.append({
                            'type': 'suicide_ideation',
                            'severity': 'high',
                            'message': rule['message'],
                            'action': rule['action']
                        })
        
        return flags
    
    def create_panic_assistant(self):
        """Create panic attack assistant interface"""
        with gr.Group():
            gr.Markdown("## 🆘 Asisten Serangan Panik")
            
            with gr.Tabs():
                with gr.Tab("Pernapasan"):
                    gr.Markdown("### Teknik Pernapasan")
                    
                    breathing_type = gr.Dropdown(
                        choices=[
                            ("Pernapasan Kotak (4-4-4-4)", "box"),
                            ("4-7-8 Breathing", "478"),
                            ("Pernapasan Dalam", "deep")
                        ],
                        label="Pilih teknik pernapasan",
                        value="box"
                    )
                    
                    start_breathing = gr.Button("🫁 Mulai Latihan Pernapasan", variant="primary")
                    breathing_display = gr.HTML()
                    
                    start_breathing.click(
                        self.breathing_exercise,
                        inputs=[breathing_type],
                        outputs=[breathing_display]
                    )
                
                with gr.Tab("Grounding"):
                    gr.Markdown("### Teknik Grounding 5-4-3-2-1")
                    
                    start_grounding = gr.Button("🌟 Mulai Grounding", variant="primary")
                    grounding_display = gr.HTML()
                    
                    start_grounding.click(
                        self.grounding_exercise,
                        inputs=[],
                        outputs=[grounding_display]
                    )
                
                with gr.Tab("Sumber Daya"):
                    gr.Markdown("### Sumber Daya Darurat")
                    
                    gr.HTML("""
                        <div style='padding: 20px; background-color: #FED7D7; border-radius: 8px; text-align: center;'>
                            <h3 style='color: #C53030;'>Jika Anda mengalami krisis:</h3>
                            <p><strong>Layanan Darurat: 112</strong></p>
                            <p><strong>Lifeline Indonesia: 021-85203010</strong></p>
                            <button onclick="window.parent.postMessage('go-crisis', '*')" 
                                    style='background-color: #C53030; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px;'>
                                🚨 Akses Halaman Krisis
                            </button>
                        </div>
                    """)
    
    def breathing_exercise(self, breathing_type: str):
        """Generate breathing exercise visualization"""
        if breathing_type == "box":
            return """
                <div style='text-align: center; padding: 20px;'>
                    <h3>🫁 Pernapasan Kotak (4-4-4-4)</h3>
                    <div style='width: 200px; height: 200px; border: 3px solid #4299E1; margin: 20px auto; border-radius: 10px; position: relative;'>
                        <div style='position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 18px; font-weight: bold;'>
                            Tarik Napas<br>4 detik
                        </div>
                    </div>
                    <p><strong>Instruksi:</strong></p>
                    <ol style='text-align: left; max-width: 300px; margin: 0 auto;'>
                        <li>Tarik napas selama 4 detik</li>
                        <li>Tahan napas selama 4 detik</li>
                        <li>Keluarkan napas selama 4 detik</li>
                        <li>Tahan kosong selama 4 detik</li>
                        <li>Ulangi 5-10 kali</li>
                    </ol>
                </div>
            """
        elif breathing_type == "478":
            return """
                <div style='text-align: center; padding: 20px;'>
                    <h3>🫁 4-7-8 Breathing</h3>
                    <div style='width: 200px; height: 200px; border: 3px solid #48BB78; margin: 20px auto; border-radius: 50%; position: relative;'>
                        <div style='position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 16px; font-weight: bold; text-align: center;'>
                            Tarik Napas<br>4 detik
                        </div>
                    </div>
                    <p><strong>Instruksi:</strong></p>
                    <ol style='text-align: left; max-width: 300px; margin: 0 auto;'>
                        <li>Tarik napas selama 4 detik</li>
                        <li>Tahan napas selama 7 detik</li>
                        <li>Keluarkan napas perlahan selama 8 detik</li>
                        <li>Ulangi 4-8 kali</li>
                    </ol>
                </div>
            """
        else:
            return """
                <div style='text-align: center; padding: 20px;'>
                    <h3>🫁 Pernapasan Dalam</h3>
                    <div style='width: 200px; height: 200px; border: 3px solid #9F7AEA; margin: 20px auto; border-radius: 50%; position: relative;'>
                        <div style='position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 16px; font-weight: bold; text-align: center;'>
                            Tarik Napas<br>Perlahan
                        </div>
                    </div>
                    <p><strong>Instruksi:</strong></p>
                    <ol style='text-align: left; max-width: 300px; margin: 0 auto;'>
                        <li>Tarik napas perlahan melalui hidung</li>
                        <li>Biarkan perut mengembang</li>
                        <li>Keluarkan napas perlahan melalui mulut</li>
                        <li>Fokus pada pernapasan Anda</li>
                        <li>Ulangi selama 5-10 menit</li>
                    </ol>
                </div>
            """
    
    def grounding_exercise(self):
        """Generate grounding exercise interface"""
        return """
            <div style='text-align: center; padding: 20px;'>
                <h3>🌟 Grounding 5-4-3-2-1</h3>
                <p><strong>Gunakan indera Anda untuk kembali ke saat ini:</strong></p>
                
                <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0;'>
                    <div style='background-color: #D6F5E5; padding: 15px; border-radius: 8px;'>
                        <h4>👁️ 5 HAL YANG ANDA LIHAT</h4>
                        <p>Lihat sekeliling dan identifikasi 5 benda</p>
                    </div>
                    
                    <div style='background-color: #FFD9C7; padding: 15px; border-radius: 8px;'>
                        <h4>👂 4 HAL YANG ANDA DENGAR</h4>
                        <p>Dengarkan dan identifikasi 4 suara</p>
                    </div>
                    
                    <div style='background-color: #E8D8FF; padding: 15px; border-radius: 8px;'>
                        <h4>✋ 3 HAL YANG ANDA SENTUH</h4>
                        <p>Sentuh dan identifikasi 3 tekstur</p>
                    </div>
                    
                    <div style='background-color: #D8F0FF; padding: 15px; border-radius: 8px;'>
                        <h4>👃 2 HAL YANG ANDA CIUM</h4>
                        <p>Cium dan identifikasi 2 bau</p>
                    </div>
                    
                    <div style='background-color: #F7F1E5; padding: 15px; border-radius: 8px;'>
                        <h4>👅 1 HAL YANG ANDA RASA</h4>
                        <p>Rasakan dan identifikasi 1 rasa</p>
                    </div>
                </div>
                
                <p><em>Lakukan latihan ini perlahan dan fokus pada setiap indera</em></p>
            </div>
        """
    
    def create_quick_screening(self):
        """Create quick screening interface (PHQ-2)"""
        instrument = self.instruments['phq2']
        
        gr.Markdown(f"## {instrument['title']['id']}")
        gr.Markdown(f"*{instrument['description']['id']}*")
        gr.Markdown(f"**{instrument['timeframe']['id']}**")
        
        # Create input components
        item_ids = []
        inputs = []
        for item in instrument['items']:
            item_ids.append(item['id'])
            inputs.append(gr.Radio(
                choices=[(opt['label']['id'], opt['value']) for opt in item['options']],
                label=item['text']['id'],
                type="value"
            ))
        
        submit_btn = gr.Button("Kirim Jawaban", variant="primary")
        result_output = gr.HTML()
        
        def process_quick_screening(*values):
            # Map positional arguments to item IDs
            responses_dict = dict(zip(item_ids, values))
            
            score = self.calculate_score('phq2', responses_dict)
            interpretation = self.get_interpretation('phq2', score)
            
            html = f"""
                <div style='padding: 20px; background-color: #F7FAFC; border-radius: 8px;'>
                    <h3>Hasil PHQ-2</h3>
                    <p><strong>Skor Total:</strong> {score['total']}/{score['max_score']}</p>
                    <p><strong>Interpretasi:</strong> {interpretation['label']['id']}</p>
                    <p><strong>Deskripsi:</strong> {interpretation['description']['id']}</p>
            """
            
            if score['total'] >= 3:
                html += """
                    <div style='background-color: #FED7D7; border: 1px solid #FC8181; border-radius: 8px; padding: 15px; margin-top: 15px;'>
                        <h4 style='color: #C53030;'>⚠️ Screening Positif</h4>
                        <p>Hasil menunjukkan adanya gejala depresi yang memerlukan evaluasi lebih lanjut.</p>
                        <p><strong>Rekomendasi:</strong> Lanjutkan ke PHQ-9 untuk evaluasi lengkap.</p>
                    </div>
                """
            
            html += "</div>"
            return html
        
        submit_btn.click(
            process_quick_screening,
            inputs=inputs,
            outputs=[result_output]
        )
    
    def create_full_assessment(self):
        """Create full assessment interface"""
        with gr.Row():
            with gr.Column():
                gr.Markdown("## Pilih Instrumen Evaluasi")
                
                instrument_choice = gr.CheckboxGroup(
                    choices=[
                        ("PHQ-9 (Depresi)", "phq9"),
                        ("GAD-7 (Kecemasan)", "gad7"),
                        ("DASS-21 (Distress)", "dass21"),
                        ("CBI (Burnout)", "cbi")
                    ],
                    label="Pilih satu atau beberapa instrumen"
                )
                
                start_assessment = gr.Button("Mulai Evaluasi", variant="primary")
            
            with gr.Column():
                assessment_area = gr.HTML()
        
        def start_assessment_callback(instruments):
            if not instruments:
                return "<p>Silakan pilih setidaknya satu instrumen untuk evaluasi.</p>"
            
            html = "<div style='padding: 20px;'>"
            
            for instrument_id in instruments:
                instrument = self.instruments[instrument_id]
                html += f"""
                    <div style='margin-bottom: 30px; padding: 20px; background-color: #F7FAFC; border-radius: 8px;'>
                        <h3>{instrument['title']['id']}</h3>
                        <p><em>{instrument['description']['id']}</em></p>
                        <p><strong>{instrument['timeframe']['id']}</strong></p>
                """
                
                for item in instrument['items']:
                    html += f"""
                        <div style='margin: 15px 0; padding: 15px; background-color: white; border-radius: 5px;'>
                            <p><strong>{item['text']['id']}</strong></p>
                            <div style='display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px;'>
                    """
                    
                    for option in item['options']:
                        html += f"""
                            <label style='display: flex; align-items: center; padding: 8px; background-color: #EDF2F7; border-radius: 5px; cursor: pointer;'>
                                <input type='radio' name='{item['id']}' value='{option['value']}' style='margin-right: 8px;'>
                                {option['label']['id']}
                            </label>
                        """
                    
                    html += "</div></div>"
                
                html += "</div>"
            
            html += """
                <button onclick="submitFullAssessment()" style='background-color: #4299E1; color: white; padding: 12px 24px; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; margin-top: 20px;'>
                    Kirim Semua Evaluasi
                </button>
            </div>
            """
            
            return html
        
        start_assessment.click(
            start_assessment_callback,
            inputs=[instrument_choice],
            outputs=[assessment_area]
        )
    
    def create_results_interface(self):
        """Create results and interpretation interface"""
        gr.Markdown("## 📊 Hasil dan Interpretasi Multi-Standar")
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("### Input Data untuk Analisis")
                
                # Example input fields for demonstration
                phq9_score = gr.Number(label="PHQ-9 Score", minimum=0, maximum=27, value=0)
                gad7_score = gr.Number(label="GAD-7 Score", minimum=0, maximum=21, value=0)
                dass21_depression = gr.Number(label="DASS-21 Depression", minimum=0, maximum=42, value=0)
                
                analyze_button = gr.Button("Analisis Multi-Standar", variant="primary")
            
            with gr.Column():
                results_display = gr.HTML()
        
        def analyze_results(phq9, gad7, dass21_dep):
            html = """
                <div style='padding: 20px; background-color: #F7FAFC; border-radius: 8px;'>
                    <h3>Interpretasi Multi-Standar</h3>
            """
            
            # PHQ-9 interpretation
            if phq9 > 0:
                phq9_interp = self.get_interpretation('phq9', {'total': phq9})
                html += f"""
                    <div style='margin-bottom: 15px; padding: 15px; background-color: #D6F5E5; border-radius: 8px;'>
                        <h4>PHQ-9 (Depresi)</h4>
                        <p><strong>Skor:</strong> {phq9}/27</p>
                        <p><strong>Kategori:</strong> {phq9_interp['label']['id']}</p>
                        <p><strong>Deskripsi:</strong> {phq9_interp['description']['id']}</p>
                    </div>
                """
            
            # GAD-7 interpretation
            if gad7 > 0:
                gad7_interp = self.get_interpretation('gad7', {'total': gad7})
                html += f"""
                    <div style='margin-bottom: 15px; padding: 15px; background-color: #FFD9C7; border-radius: 8px;'>
                        <h4>GAD-7 (Kecemasan)</h4>
                        <p><strong>Skor:</strong> {gad7}/21</p>
                        <p><strong>Kategori:</strong> {gad7_interp['label']['id']}</p>
                        <p><strong>Deskripsi:</strong> {gad7_interp['description']['id']}</p>
                    </div>
                """
            
            # Cross-walk analysis
            html += """
                <div style='margin-top: 20px; padding: 15px; background-color: #E8D8FF; border-radius: 8px;'>
                    <h4>Analisis Cross-Walk</h4>
                    <p><strong>Perbandingan Keparahan:</strong></p>
                    <ul>
            """
            
            if phq9 > 0 and gad7 > 0:
                html += f"""
                    <li>PHQ-9 vs GAD-7: {self.compare_severity(phq9, gad7)}</li>
                """
            
            html += """
                    </ul>
                </div>
            </div>
            """
            
            return html
        
        analyze_button.click(
            analyze_results,
            inputs=[phq9_score, gad7_score, dass21_depression],
            outputs=[results_display]
        )
    
    def compare_severity(self, phq9_score: int, gad7_score: int) -> str:
        """Compare severity between instruments"""
        phq9_severity = "minimal" if phq9_score <= 4 else "mild" if phq9_score <= 9 else "moderate" if phq9_score <= 14 else "severe"
        gad7_severity = "minimal" if gad7_score <= 4 else "mild" if gad7_score <= 9 else "moderate" if gad7_score <= 14 else "severe"
        
        return f"Depresi: {phq9_severity}, Kecemasan: {gad7_severity}"
    
    def create_screening_interface(self):
        """Create the screening interface tab - combines quick and full assessment"""
        with gr.Tabs():
            with gr.Tab("Skrining Cepat"):
                self.create_quick_screening()
            
            with gr.Tab("Evaluasi Lengkap"):
                self.create_full_assessment()
    
    def create_education_interface(self):
        """Create education interface"""
        gr.Markdown("## 📚 Edukasi Kesehatan Mental")
        
        with gr.Tabs():
            with gr.Tab("Depresi"):
                gr.Markdown("""
                    ## 😔 Depresi
                    
                    ### Definisi
                    Depresi adalah gangguan suasana perasaan yang ditandai oleh perasaan sedih yang terus-menerus dan kehilangan minat dalam aktivitas sehari-hari.
                    
                    ### Gejala Umum
                    - Perasaan sedih, kosong, atau putus asa
                    - Kehilangan minat atau kesenangan dalam aktivitas
                    - Kelelahan atau kehilangan energi
                    - Gangguan tidur (insomnia atau hipersomnia)
                    - Perubahan nafsu makan
                    - Kesulitan berkonsentrasi
                    - Perasaan tidak berharga atau bersalah
                    - Pikiran tentang kematian atau bunuh diri
                    
                    ### Penyebab dan Faktor Risiko
                    - Faktor biologis dan genetik
                    - Faktor psikologis (trauma, stres)
                    - Faktor lingkungan dan sosial
                    - Kejadian hidup yang menantang
                    
                    ### Pengobatan
                    - Terapi psikologis (CBT, IPT, dll.)
                    - Obat antidepresan (jika diperlukan)
                    - Kombinasi terapi dan obat
                    - Perubahan gaya hidup dan self-care
                """)
            
            with gr.Tab("Kecemasan"):
                gr.Markdown("""
                    ## 😰 Kecemasan
                    
                    ### Definisi
                    Kecemasan adalah respons normal terhadap stres, tetapi dapat menjadi gangguan jika berlebihan, berlangsung lama, dan mengganggu fungsi sehari-hari.
                    
                    ### Gejala Umum
                    - Kekhawatiran berlebihan yang sulit dikendalikan
                    - Gelisah atau merasa tegang
                    - Mudah lelah
                    - Kesulitan berkonsentrasi
                    - Gangguan tidur
                    - Gejala fisik: detak jantung cepat, berkeringat, gemetar
                    
                    ### Jenis Gangguan Kecemasan
                    - Gangguan Kecemasan Umum (GAD)
                    - Serangan Panik
                    - Fobia Spesifik
                    - Kecemasan Sosial
                    - PTSD dan lainnya
                    
                    ### Strategi Coping
                    - Teknik relaksasi dan pernapasan
                    - Mindfulness dan meditasi
                    - Terapi kognitif-perilaku
                    - Olahraga teratur
                    - Manajemen stres
                """)
            
            with gr.Tab("Burnout"):
                gr.Markdown("""
                    ## 🔥 Burnout
                    
                    ### Definisi
                    Burnout adalah keadaan kelelahan emosional, mental, dan fisik yang disebabkan oleh stres berkepanjangan, terutama terkait pekerjaan.
                    
                    ### Tiga Dimensi Utama
                    1. **Kelelahan Emosional:** Merasa terkuras dan kehabisan energi
                    2. **Depersonalisasi:** Sikap sinis dan terpisah dari pekerjaan
                    3. **Reduced Personal Accomplishment:** Perasaan tidak berhasil dan tidak kompeten
                    
                    ### Gejala
                    - Kelelahan kronis
                    - Kehilangan motivasi
                    - Sinisme dan negativitas
                    - Gangguan tidur
                    - Masalah kesehatan fisik
                    - Isolasi sosial
                    
                    ### Pencegahan dan Penanganan
                    - Work-life balance
                    - Manajemen stres
                    - Istirahat yang cukup
                    - Dukungan sosial
                    - Batasan yang sehat
                    - Self-care teratur
                """)
            
            with gr.Tab("Self-Care"):
                gr.Markdown("""
                    ## 💚 Self-Care dan Wellness
                    
                    ### Pentingnya Self-Care
                    Self-care adalah praktik sadar untuk menjaga kesehatan fisik, mental, dan emosional Anda.
                    
                    ### Dimensi Self-Care
                    
                    #### 🧠 Kesehatan Mental
                    - Terapi atau konseling jika diperlukan
                    - Mindfulness dan meditasi
                    - Jurnal reflektif
                    - Batasan yang sehat
                    
                    #### 💪 Kesehatan Fisik
                    - Olahraga teratur
                    - Tidur yang cukup
                    - Nutrisi seimbang
                    - Perawatan medis rutin
                    
                    #### ❤️ Kesehatan Emosional
                    - Ekspresi emosi yang sehat
                    - Dukungan sosial
                    - Aktivitas yang menyenangkan
                    - Relaksasi dan hobi
                    
                    #### 🌱 Kesehatan Spiritual
                    - Praktik spiritual atau keagamaan
                    - Refleksi dan introspeksi
                    - Koneksi dengan alam
                    - Tujuan dan makna hidup
                    
                    ### Tips Praktis
                    - Mulai dengan langkah kecil
                    - Konsisten daripada sempurna
                    - Dengarkan kebutuhan Anda
                    - Jangan ragu mencari bantuan
                """)
    
    def create_interface(self):
        """Create the main Gradio interface"""
        css = """
        .gradio-container {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .tab-button {
            font-size: 16px !important;
            padding: 12px 20px !important;
        }
        .tab-button.selected {
            background-color: #D6F5E5 !important;
            color: #2D3748 !important;
        }
        """
        
        with gr.Blocks(theme=gr.themes.Soft(), css=css, title="Screening Kesehatan Mental") as app:
            # Header
            gr.Markdown("""
                # 🧠 Screening Kesehatan Mental
                ## Platform Evaluasi Depresi, Kecemasan, dan Burnout
                
                **⚠️ Platform ini untuk tujuan edukatif dan skrining saja. Bukan pengganti evaluasi profesional.**
            """)
            
            # Navigation
            with gr.Tabs():
                with gr.Tab("🏠 Beranda"):
                    self.create_screening_interface()
                
                with gr.Tab("📊 Hasil & Interpretasi"):
                    self.create_results_interface()
                
                with gr.Tab("🆘 Asisten Panik"):
                    self.create_panic_assistant()
                
                with gr.Tab("📚 Edukasi"):
                    self.create_education_interface()
                
                with gr.Tab("ℹ️ Tentang"):
                    gr.Markdown("""
                        ## Tentang Platform Ini
                        
                        Platform screening kesehatan mental ini dikembangkan berdasarkan instrumen terstandarisasi dan validasi ilmiah.
                        
                        ### Instrumen yang Digunakan
                        - **PHQ-9**: Patient Health Questionnaire-9 untuk depresi
                        - **GAD-7**: Generalized Anxiety Disorder-7 untuk kecemasan
                        - **DASS-21**: Depression Anxiety Stress Scales untuk distress psikologis
                        - **CBI**: Copenhagen Burnout Inventory untuk burnout
                        
                        ### Fitur Utama
                        - Skrining cepat dan evaluasi lengkap
                        - Interpretasi multi-standar
                        - Asisten serangan panik
                        - Fitur keselamatan dan triase risiko
                        - Edukasi kesehatan mental
                        
                        ### Privasi dan Keamanan
                        - Semua data diproses secara lokal
                        - Tidak ada penyimpanan data di server
                        - Privasi maksimal terjamin
                        
                        ### Disclaimer
                        Platform ini untuk tujuan edukatif dan skrining awal saja. 
                        Tidak menggantikan evaluasi profesional oleh tenaga kesehatan mental berkualifikasi.
                        
                        Jika mengalami krisis, segera hubungi layanan darurat.
                    """)
            
            # Footer with emergency contacts
            gr.HTML("""
                <div style='margin-top: 40px; padding: 20px; background-color: #FED7D7; border-radius: 8px; text-align: center;'>
                    <h3 style='color: #C53030; margin-top: 0;'>🚨 Krisis Darurat</h3>
                    <p><strong>Layanan Darurat: 112 | Lifeline Indonesia: 021-85203010</strong></p>
                    <p>Jika mengalami pikiran untuk menyakiti diri sendiri, segera hubungi layanan darurat.</p>
                </div>
            """)
        
        return app

# Create and launch the app
if __name__ == "__main__":
    app = MentalHealthScreeningApp()
    interface = app.create_interface()
    interface.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        share=False
    )
