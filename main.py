import openai
import os
import kivy
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
openai.api_key = api_key

# Inicializar sintetizador de voz
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Ajusta a velocidade da fala

# Inicializar reconhecimento de voz
recognizer = sr.Recognizer()
microphone = sr.Microphone()

class Assistente(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.label = Label(text="Aguardando... Diga 'Chat' para ativar.", font_size="20sp")
        self.add_widget(self.label)
        Clock.schedule_interval(self.ouvir_continuamente, 1)  # Chama a função a cada 1s

    def ouvir_continuamente(self, dt):
        """Fica ouvindo o microfone continuamente e ativa ao detectar 'Chat'."""
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            try:
                print("Ouvindo...")
                audio = recognizer.listen(source, timeout=5)
                texto = recognizer.recognize_google(audio, language="pt-BR").lower()
                print(f"Você disse: {texto}")

                if "chat" in texto:
                    self.label.text = "Ativando assistente..."
                    Clock.schedule_once(lambda dt: self.processar_comando(), 0)  # Processa após ativação

            except sr.UnknownValueError:
                pass
            except sr.RequestError:
                self.label.text = "Erro na conexão com reconhecimento de voz."
            except Exception as e:
                print(f"Erro inesperado: {e}")

    def processar_comando(self):
        """Espera uma pergunta após ativação e responde."""
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            try:
                self.label.text = "Fale agora sua pergunta..."
                print("Fale agora sua pergunta...")
                audio = recognizer.listen(source, timeout=10)
                pergunta = recognizer.recognize_google(audio, language="pt-BR")
                print(f"Pergunta detectada: {pergunta}")

                resposta = obter_resposta(pergunta)
                self.label.text = f"Você: {pergunta}\nAssistente: {resposta}"
                falar_resposta(resposta)

            except sr.UnknownValueError:
                self.label.text = "Não entendi o que você disse."
            except sr.RequestError:
                self.label.text = "Erro ao conectar ao serviço de voz."
            except Exception as e:
                print(f"Erro inesperado: {e}")

class AssistenteApp(App):
    def build(self):
        return Assistente()

def obter_resposta(pergunta):
    """Obtém resposta do ChatGPT"""
    try:
        resposta = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": pergunta}]
        )
        return resposta["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Erro na API OpenAI: {e}")
        return "Não consegui obter uma resposta no momento."

def falar_resposta(texto):
    """Fala a resposta em voz alta"""
    engine.say(texto)
    engine.runAndWait()

if __name__ == "__main__":
    AssistenteApp().run()
