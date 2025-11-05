# LikeC4 Template

This template is an example of how to use LikeC4.  
Contains:

- LikeC4 sources ([`/src`](./src/))
- Model validation ([`/test/validate-model.spec.ts`](./test/validate-model.spec.ts))
- Deploy to github pages ([`pages.yml`](./.github/workflows/pages.yml))
- Project configuration with custom generator ([`likec4.config.ts`](./likec4.config.ts))  

Demo - [https://template.likec4.dev](https://template.likec4.dev/view/cloud)

Try it online:

[![Open in StackBlitz](https://developer.stackblitz.com/img/open_in_stackblitz.svg)](https://stackblitz.com/~/github.com/likec4/template?file=src/model.c4)

Or:
-  [github.dev](https://github.dev/likec4/template/blob/main/src/model.c4)
-  [vscode.dev](https://vscode.dev/github/likec4/template/src/model.c4)

> You will get popup suggesting to install "LikeC4" extension.  
> Agree to get syntax highlighting, completions and other features in likec4 files

## Setup your local environment

LikeC4 works best in an IDE, there are extensions/plugins for both Visual Studio Code and IntelliJ idea, however the IntelliJ plugin is not currently maintained and therefore Visual Studio Code is the suggested editor of choice.

>The following instructions are for Visual Studio Code on MacOS, once completed you should be able to run likec4 locally from the command line, using the instructions on the cli section below.

### Install Visual Studio Code
Download and install Visual Studio Code from the [official VS Code page](https://code.visualstudio.com/download#). 
The simplest installation is to download the zip file and extract the app, but choose the option you're most familiar with.

Once installed, complete the setup wizard within the app and see the [setup overview guide](https://code.visualstudio.com/docs/setup/setup-overview) for familiarisation.

### Install extension for Visual Studio Code
Navigate to the [exension page](https://marketplace.visualstudio.com/items?itemName=likec4.likec4-vscode) and click the `install` button, 
it should take you to the extensions window inside VSC to complete the installation.

After installation, when a `.c4 file` is opened in the editor there will be an `'open preview'` link directly above any `view` definition. Clicking this link opens the view in the `Diagram Preview` tab.

### Install Node.js
> LikeC4 requires Node.js version 20+

Check if you have a compatible version already installed
```bash
node -v
```
Install/update node using your terminal or download and run the [.pkg installer](https://nodejs.org/en/download)


## How-to

1. Create a new repository from this template
2. Pull your repository and open in VSCode
3. Install suggested [LikeC4 extension](https://marketplace.visualstudio.com/items?itemName=likec4.likec4)

Now you can edit likec4 sources, refactor, navigate and preview diagrams.

### CLI

You can install globally, locally and use scripts from `package.json`, or just via `npx`  
Check [documentation](https://likec4.dev/tooling/cli/)  

> LikeC4 requires Node.js version 20+  

To start local server with live reload (for development or quick preview)  
The app should start and load a localhost webapp in your default browser (e.g. http://localhost:5173/) showing your models
Inside the project folder:

```bash
npx likec4 start
```

Export to PNG:

```bash
npx likec4 export png -o png
```

Documentation: https://likec4.dev/docs/tools/cli/

### Custom generator

[`likec4.config.ts`](./likec4.config.ts) includes an example of custom generator that generates CSV file with relationships:

```bash
npm run generate:relationships-csv
```

### Model validation

[`test/validate-model.spec.ts`](./test/validate-model.spec.ts) includes an example of model validation tests:

```bash
npm run test
```

> Check [documentation](https://likec4.dev/guides/validate-your-model/) for more details

### Deployment

Deployment is the same as for any project built with [vite](https://vitejs.dev/).

1. Build static site (export to HTML, ready for deployment):

```bash
npx likec4 build -o ./dist
```
> Check `npx likec4 build --help` for options and examples

2. Upload `./dist` folder to your hosting

#### Github Pages

This template contains workflow to deploy to github pages on every push to `main` branch.  
Check [`.github/workflows/pages.yml`](./.github/workflows/pages.yml)

## License

This project is released under the [MIT License](LICENSE)
