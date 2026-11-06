"""Testes das solicitações — o usuário classifica; a orientação da IA é sempre simulada (mock)."""

SOLICITACAO_EXEMPLO = {
    "titulo": "Impressora não imprime",
    "descricao": "Minha impressora parou de imprimir e aparece um erro de driver.",
    "categoria": "Hardware",
    "prioridade": "Média",
}


def test_opcoes_de_classificacao(cliente, auth):
    resposta = cliente.get("/opcoes", headers=auth)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert "Hardware" in corpo["categorias"]
    assert corpo["prioridades"] == ["Baixa", "Média", "Alta"]
    assert corpo["equipes"]["Rede"] == "Infraestrutura"


def test_tria_abre_chamado_automatico_roteado(cliente, auth, triagem_mockada):
    """Fluxo 'não resolveu': a Tria classifica o relato e abre o chamado para a equipe certa."""
    resposta = cliente.post(
        "/solicitacoes/auto",
        json={"descricao": "Meu computador nao liga, ja troquei a tomada e nada."},
        headers=auth,
    )
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["titulo"] == triagem_mockada["titulo"]
    assert corpo["categoria"] == "Hardware"
    assert corpo["prioridade"] == "Alta"
    assert corpo["equipe"] == "Suporte Técnico"
    assert corpo["orientacao"] == triagem_mockada["resumo"]
    assert corpo["origem"] == "tria"


def test_chamado_automatico_aparece_na_fila_do_tecnico(cliente, auth, auth_tecnico, triagem_mockada):
    cliente.post("/solicitacoes/auto", json={"descricao": "Impressora pegando fogo de erro."}, headers=auth)
    fila = cliente.get("/solicitacoes", headers=auth_tecnico).json()
    assert len(fila) == 1
    assert fila[0]["origem"] == "tria"
    assert fila[0]["equipe"] == "Suporte Técnico"


def test_chamado_automatico_sem_login_retorna_401(cliente, triagem_mockada):
    resposta = cliente.post("/solicitacoes/auto", json={"descricao": "qualquer problema de ti aqui"})
    assert resposta.status_code == 401


def test_abrir_solicitacao_guarda_classificacao_e_orientacao_da_ia(cliente, auth, orientacao_mockada):
    resposta = cliente.post("/solicitacoes", json=SOLICITACAO_EXEMPLO, headers=auth)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id"] == 1
    assert corpo["solicitante"] == "Ana Souza"
    assert corpo["titulo"] == SOLICITACAO_EXEMPLO["titulo"]
    assert corpo["categoria"] == SOLICITACAO_EXEMPLO["categoria"]
    assert corpo["prioridade"] == SOLICITACAO_EXEMPLO["prioridade"]
    assert corpo["equipe"] == "Suporte Técnico"  # Hardware é atendido pelo Suporte Técnico
    assert corpo["origem"] == "manual"
    assert corpo["orientacao"] == orientacao_mockada
    assert corpo["status"] == "Aberta"


def test_solicitacao_manual_roteia_para_a_equipe_da_categoria(cliente, auth, orientacao_mockada):
    resposta = cliente.post(
        "/solicitacoes",
        json={**SOLICITACAO_EXEMPLO, "categoria": "Rede"},
        headers=auth,
    )
    assert resposta.json()["equipe"] == "Infraestrutura"  # Rede vai para a Infraestrutura


def test_abrir_solicitacao_sem_login_retorna_401(cliente, orientacao_mockada):
    resposta = cliente.post("/solicitacoes", json=SOLICITACAO_EXEMPLO)
    assert resposta.status_code == 401


def test_usuario_ve_somente_as_proprias_solicitacoes(cliente, auth, auth_tecnico, orientacao_mockada):
    cliente.post("/solicitacoes", json=SOLICITACAO_EXEMPLO, headers=auth)
    cliente.post(
        "/solicitacoes",
        json={**SOLICITACAO_EXEMPLO, "titulo": "Acesso ao sistema acadêmico", "categoria": "Acesso e senhas"},
        headers=auth_tecnico,
    )

    resposta = cliente.get("/solicitacoes", headers=auth)
    solicitacoes = resposta.json()
    assert len(solicitacoes) == 1
    assert solicitacoes[0]["solicitante"] == "Ana Souza"


def test_tecnico_ve_a_fila_inteira(cliente, auth, auth_tecnico, orientacao_mockada):
    cliente.post("/solicitacoes", json=SOLICITACAO_EXEMPLO, headers=auth)
    cliente.post(
        "/solicitacoes",
        json={**SOLICITACAO_EXEMPLO, "titulo": "Acesso ao sistema acadêmico", "categoria": "Acesso e senhas"},
        headers=auth_tecnico,
    )

    resposta = cliente.get("/solicitacoes", headers=auth_tecnico)
    solicitacoes = resposta.json()
    assert len(solicitacoes) == 2
    assert solicitacoes[0]["solicitante"] == "Carlos Lima"  # mais recente primeiro
    assert solicitacoes[1]["solicitante"] == "Ana Souza"


def test_admin_tambem_ve_a_fila_inteira(cliente, auth, auth_admin, orientacao_mockada):
    cliente.post("/solicitacoes", json=SOLICITACAO_EXEMPLO, headers=auth)
    resposta = cliente.get("/solicitacoes", headers=auth_admin)
    solicitacoes = resposta.json()
    assert len(solicitacoes) == 1
    assert solicitacoes[0]["solicitante"] == "Ana Souza"


def test_titulo_muito_curto_retorna_422(cliente, auth, orientacao_mockada):
    resposta = cliente.post("/solicitacoes", json={**SOLICITACAO_EXEMPLO, "titulo": "oi"}, headers=auth)
    assert resposta.status_code == 422


def test_categoria_fora_do_catalogo_retorna_422(cliente, auth, orientacao_mockada):
    resposta = cliente.post(
        "/solicitacoes", json={**SOLICITACAO_EXEMPLO, "categoria": "Jardinagem"}, headers=auth
    )
    assert resposta.status_code == 422


def test_prioridade_invalida_retorna_422(cliente, auth, orientacao_mockada):
    resposta = cliente.post(
        "/solicitacoes", json={**SOLICITACAO_EXEMPLO, "prioridade": "Urgentíssima"}, headers=auth
    )
    assert resposta.status_code == 422


def test_falha_na_ia_retorna_502(cliente, auth, monkeypatch):
    def ia_quebrada(*dados):
        raise RuntimeError("API da IA fora do ar")

    monkeypatch.setattr("app.ia.gerar_orientacao", ia_quebrada)
    resposta = cliente.post("/solicitacoes", json=SOLICITACAO_EXEMPLO, headers=auth)
    assert resposta.status_code == 502
