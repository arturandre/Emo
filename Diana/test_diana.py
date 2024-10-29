import requests

url = 'https://dianaapi-543834107372.us-central1.run.app'
accessName='External-Dev'
key='cba401af31b045de4b45cfb82df9ffe62ecc2b99ca9edbc2aef1738868e3745a'
session = None
token = None

def create_session():
    token = requests.get(
        url+'/token',
        params={
            'key':key,
            'accessName': accessName
        }
    ).json()['token']
    print(token)
    return token, requests.get(
        url+'/session',
        headers={
            'Authorization': 'Bearer '+ token
        }
    ).json()['session']
    
def call_diana(text, session, token):
    try:
        resp = requests.post(
            url+'/textIntent',
            json={
                'session':session,
                'text': text
            },
            headers={
                'Authorization': 'Bearer '+ token
            }
        )
        return resp.json()['responses'][0]['text']
    except Exception as e:
        print('error calling Diana API: ', e)
        create_session()
        return "Desculpe, não entendi o que você disse."

token, session = create_session()

prompt = """
	IMPORTANTE:
	 1. Além do que você pode fazer, você agora também consegue executar ações.
	 2. RESPONDA SEMPRE EM JSON!!
	AÇÔES QUE VOCÊ PODE EXECUTAR:
	 - deslocar_linear
	 - falar
	 - acenar
	Exemplos de cada função:
	 - deslocar_linear(1.5) -- Desloca 1.5 metros para frente
	 - falar("Olá, meu nome é Diana!") -- Fala algo
	 - acenar() -- Usa o manipulador para acenar
	 
	Exemplo de utilização das funções:
	Texto do usuário:
	 'Ande 2 metros e diga oi'
	Sua Resposta esperada:
	 '''{{
	     'deslocar_linear': 1.5,
	     'falar': 'Olá'
	 }}'''
	VALENDO!

	TEXTO DO USUÁRIO:
	 {input}
	SUA RESPOSTA:
"""

out = call_diana(
            text=prompt.format(input='Ande 0.2 metros e dia um oi para a galera'),
            session=session,
            token=token
        )
print(eval(out))
