# Maquette 3D – Maison R+1

Visionneuse 3D de la maison (rez-de-chaussée + étage), en site statique : aucune compilation, aucune dépendance à installer pour l'héberger.

## Contenu

```
index.html                 la visionneuse (Three.js r147)
models/maison_3D.glb       le modèle 3D complet (RDC + étage)
vendor/                    Three.js + GLTFLoader + OrbitControls (copie locale, aucun CDN)
plans/                     plans PDF d'origine (RDC et étage)
source/build_model.py      script Python qui génère le .glb
_headers                   en-têtes HTTP pour Cloudflare Pages
```

## Utilisation de la visionneuse

- **Rez-de-chaussée / Étage** : afficher seulement le RDC, ou la maison entière.
- **Vue 3D / Vue de dessus** : changer de point de vue.
- **Mobilier / Noms des pièces** : afficher ou masquer.
- **Hauteur de coupe des murs** : abaisser les murs du niveau affiché pour voir l'intérieur.

## Tester en local

```bash
python -m http.server 8000
# puis ouvrir http://localhost:8000
```

(Le double-clic sur index.html ne suffit pas : le navigateur bloque le chargement du .glb.)

## Mettre en ligne sur Cloudflare Pages

```bash
git init
git add .
git commit -m "Maquette 3D maison R+1"
git branch -M main
git remote add origin https://github.com/VOTRE-COMPTE/maquette-maison.git
git push -u origin main
```

Dans Cloudflare : **Workers & Pages → Create → Pages → Connect to Git**, choisir le dépôt :

| Réglage                | Valeur           |
|------------------------|------------------|
| Framework preset       | None             |
| Build command          | *(laisser vide)* |
| Build output directory | `/`              |

Chaque `git push` redéploie automatiquement.

## Régénérer le modèle (optionnel)

```bash
cd source
pip install -r requirements.txt
python build_model.py      # réécrit ../models/maison_3D.glb
```

Toutes les cotes sont en mètres dans `build_model.py` (origine = coin nord-ouest du RDC).

## Utiliser le modèle dans un autre projet Three.js

```js
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
new GLTFLoader().load('models/maison_3D.glb', gltf => scene.add(gltf.scene));
```

Les objets de l'étage ont un nom qui commence par `Etage_` (ex. `Etage_Murs_0`), ceux du RDC non.
