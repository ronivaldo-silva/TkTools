# Newrecep app
O sistema coleta informações básicas do sistema Solidfalcon através do banco de dados SQL Server e exibe em uma interface gráfica.

Usa os dados para se conectar com os equipamentos Hikvision e coleta informações de usuários, faces, digitais, etc.

Capaz de configurações dos equipamentos faciais Hikvision com padrões para integrar com o sistema Solidfalcon.

Capaz de normalizar os registros de pessoas nos faciais Hikvision.
Esses registros são Entidades tipo 1 no banco de dados e nos faciais são usuários.
Para normalizar segue a ordem lógica:
1. Coleta a os registros existentes nos faciais
2. Verifica se os registros existem no banco de dados comparando os Ids (EntityId = EmployeeId)
3. Se Não existir, envia o comando para deletar do facial
4. Se existir, atualiza com as informações do banco de dados
5. Por fim, insere os registros novos no facial

Obs: Avaliar se viavel tratar visitantes diferente de condêminos.

## Run the app
flet run main.py --w --port 8501

### uv

Run as a desktop app:

```bash
uv run flet run
```

Run as a web app:

```bash
uv run flet run --web
```

For more details on running the app, refer to the [Getting Started Guide](https://docs.flet.dev/).

## Build the app

### Android

```bash
flet build apk -v
```

For more details on building and signing `.apk` or `.aab`, refer to the [Android Packaging Guide](https://docs.flet.dev/publish/android/).

### iOS

```bash
flet build ipa -v
```

For more details on building and signing `.ipa`, refer to the [iOS Packaging Guide](https://docs.flet.dev/publish/ios/).

### macOS

```bash
flet build macos -v
```

For more details on building macOS package, refer to the [macOS Packaging Guide](https://docs.flet.dev/publish/macos/).

### Linux

```bash
flet build linux -v
```

For more details on building Linux package, refer to the [Linux Packaging Guide](https://docs.flet.dev/publish/linux/).

### Windows

```bash
flet build windows -v
```

For more details on building Windows package, refer to the [Windows Packaging Guide](https://docs.flet.dev/publish/windows/).

### Web

```bash
flet build web -v
```

For more details on building Web app, refer to the [Web Packaging Guide](https://docs.flet.dev/publish/web/).
