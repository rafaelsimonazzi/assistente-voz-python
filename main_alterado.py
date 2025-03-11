import os
import threading
from openai import OpenAI
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
import speech_recognition as sr
import pyttsx3
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("A chave da API OpenAI não foi encontrada. Verifique o arquivo .env.")

# Configurar API Key
client = OpenAI(api_key=api_key)

# Inicializar sintetizador de voz
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Ajusta a velocidade da fala


# Inicializar reconhecimento de voz
recognizer = sr.Recognizer()
# Usaremos uma única instância de Microphone, mas o acesso será sincronizado
microphone = sr.Microphone()


def obter_resposta(pergunta):
    """Obtém resposta do ChatGPT"""
    try:
        resposta = client.chat.completions.create(model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": pergunta}])
        return resposta.choices[0].message.content
    except Exception as e:
        print(f"Erro na API OpenAI: {e}")
        return "Não consegui obter uma resposta no momento."


def falar_resposta(texto):
    """Fala a resposta em voz alta"""
    engine.say(texto)
    engine.runAndWait()


class Assistente(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.label = Label(text="Aguardando... Diga 'Chat' para ativar.", font_size="20sp")
        self.add_widget(self.label)

        # Flag para evitar sobreposição de comandos
        self.is_processing = False

        # Lock para sincronizar acesso ao microfone
        self.microphone_lock = threading.Lock()

        # Inicia a thread que ficará ouvindo continuamente
        threading.Thread(target=self.run_listener, daemon=True).start()

    def set_label(self, text):
        self.label.text = text

    def run_listener(self):
        """Thread que fica ouvindo a palavra de ativação e inicia o processamento do comando."""
        while True:
            try:
                with self.microphone_lock, microphone as source:
                    recognizer.adjust_for_ambient_noise(source)
                    print("Ouvindo para ativação...")
                    audio = recognizer.listen(source, timeout=5)
                    texto = recognizer.recognize_google(audio, language="pt-BR").lower()
                    print(f"Você disse (ativação): {texto}")

                if "chat" in texto and not self.is_processing:
                    self.is_processing = True
                    Clock.schedule_once(lambda dt: self.set_label("Ativando assistente..."), 0)
                    # Inicia o processamento do comando em outra thread
                    threading.Thread(target=self.processar_comando, daemon=True).start()
            except sr.UnknownValueError:
                # Se não entendeu, continua ouvindo
                continue
            except sr.RequestError:
                Clock.schedule_once(lambda dt: self.set_label("Erro na conexão com reconhecimento de voz."), 0)
            except Exception as e:
                print(f"Erro inesperado na ativação: {e}")

    def processar_comando(self):
        """Processa o comando após a ativação"""
        try:
            with self.microphone_lock, microphone as source:
                recognizer.adjust_for_ambient_noise(source)
                Clock.schedule_once(lambda dt: self.set_label("Fale agora sua pergunta..."), 0)
                print("Fale agora sua pergunta...")
                audio = recognizer.listen(source, timeout=10)
                pergunta = recognizer.recognize_google(audio, language="pt-BR")
                print(f"Pergunta detectada: {pergunta}")
        except sr.UnknownValueError:
            Clock.schedule_once(lambda dt: self.set_label("Não entendi o que você disse."), 0)
            self.is_processing = False
            return
        except sr.RequestError:
            Clock.schedule_once(lambda dt: self.set_label("Erro ao conectar ao serviço de voz."), 0)
            self.is_processing = False
            return
        except Exception as e:
            print(f"Erro inesperado durante o comando: {e}")
            self.is_processing = False
            return

        # Obter resposta da API
        resposta = obter_resposta(pergunta)

        # Atualiza a interface e fala a resposta
        Clock.schedule_once(lambda dt: self.update_ui(pergunta, resposta), 0)
        self.is_processing = False

    def update_ui(self, pergunta, resposta):
        self.label.text = f"Você: {pergunta}\nAssistente: {resposta}"
        # Fala a resposta em uma thread separada para não bloquear a UI
        threading.Thread(target=falar_resposta, args=(resposta,), daemon=True).start()


class AssistenteApp(App):
    def build(self):
        return Assistente()


if __name__ == "__main__":
    AssistenteApp().run()
