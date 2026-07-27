# Reconnaissance de bons de commande

[中文](../README.md) · [English](README.en.md) · **Français**

Cette application Windows corrige les photos de bons de livraison, regroupe les pages par commande, lit les lignes produit, vérifie indépendamment les nombres de cartons, permet une révision manuelle et exporte un fichier Excel à deux colonnes : référence produit et nombre de cartons.

L’interface bascule immédiatement entre le chinois, l’anglais et le français. Utilisez l’icône en forme de globe dans la barre d’outils ou choisissez la langue dans les Paramètres. Le changement de langue ne modifie jamais les références, numéros de commande ou preuves reconnus.

## Chaîne de reconnaissance

- orientation EXIF, comparaison des quatre rotations, détection de page et correction de perspective ;
- conservation des couleurs, réduction du bruit, correction des ombres et amélioration du contraste ;
- indices de texte et de position avec RapidOCR/ONNX en local ;
- images envoyées à l’API Responses OpenAI avec sorties Pydantic strictement structurées ;
- extraction de la page puis vérification indépendante de chaque ligne avec trois recadrages ;
- calcul final du nombre de cartons uniquement par les règles Python ;
- reprise SQLite, détection des doublons SHA-256 et cache des résultats API.

## Règle de calcul

La colonne de quantité totale n’est jamais utilisée comme nombre de cartons.

1. Une correction manuscrite non négative clairement associée est prioritaire.
2. Sinon, le nombre imprimé est conservé s’il se trouve dans un cercle clairement fermé.
3. Sinon, l’absence confirmée de cercle fermé donne zéro.
4. Un cercle incertain bloque l’export automatique et exige une vérification manuelle.

Les points, coches, traits courts, barres obliques, parenthèses et arcs ouverts ne sont pas des cercles fermés.

## Installation et démarrage

Utilisez Python 3.11 64 bits sous Windows 10/11.

1. Exécutez `install.bat`.
2. Exécutez `start.bat` ou le programme `dist\订单纸单识别器.exe`.
3. Au premier lancement, saisissez `OPENAI_API_KEY` dans les Paramètres. La clé est stockée dans le Gestionnaire d’identifiants Windows.

Pour le développement :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest -q
```

## Confidentialité et limites

Les images sont envoyées uniquement à l’API visuelle OpenAI configurée. Aucun SDK publicitaire, analytique ou de suivi n’est inclus. Ne publiez jamais `.env`, les clés API, les vrais bons de livraison, les journaux d’audit ou les exports Excel.

La précision ne peut pas être garantie à 100 %. Les images floues, les conflits O/0, I/l/1 et S/5, les cercles incertains, les pages manquantes et les écritures ambiguës nécessitent une confirmation manuelle.

Consultez les [instructions GitHub](GITHUB_UPLOAD.md), les [règles de contribution](../CONTRIBUTING.md) et la [politique de sécurité](../SECURITY.md).

