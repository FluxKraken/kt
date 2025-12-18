import os
import json
import tarfile
import tempfile
import shutil
import subprocess
import glob
from cli.db.session import get_session
from cli.db.models import Project, Template, Recipe, Asset
from sqlmodel import select

def create_bundle(project_name: str, output_path: str, overwrite: bool = False):
    """
    Export a project and its resources to a .project tarball.
    Structure:
    /project.json
    /templates/name
    /recipes/name.lua
    /assets/name
    """
    if os.path.exists(output_path) and not overwrite:
        raise FileExistsError(f"Output file '{output_path}' exists.")
        
    with get_session() as session:
        proj = session.exec(select(Project).where(Project.name == project_name)).first()
        if not proj:
            raise ValueError(f"Project '{project_name}' not found.")
            
        with tempfile.TemporaryDirectory() as tmpdir:
            # Metadata
            meta = {
                "name": proj.name,
                "created_at": str(proj.created_at)
            }
            with open(os.path.join(tmpdir, "project.json"), 'w') as f:
                json.dump(meta, f)
                
            # Templates
            tmpl_dir = os.path.join(tmpdir, "templates")
            os.makedirs(tmpl_dir)
            
            recipes_dir = os.path.join(tmpdir, "recipes")
            os.makedirs(recipes_dir)
            
            assets_dir = os.path.join(tmpdir, "assets")
            os.makedirs(assets_dir)
            
            # Export Templates
            templates = session.exec(select(Template).where(Template.project_id == proj.id)).all()
            for t in templates:
                # Sanitize filename? assume name is safe or simple
                # Template content is string
                with open(os.path.join(tmpl_dir, t.name), 'w') as f:
                    f.write(t.content)
                    
            # Export Recipes
            recipes = session.exec(select(Recipe).where(Recipe.project_id == proj.id)).all()
            for r in recipes:
                # Add .lua extension if missing for clarity? Or keep exact name. 
                # User asks "name", assuming name is identifier.
                fname = r.name + ".lua" if not r.name.endswith(".lua") else r.name
                # Be careful on import to map back to 'name'
                # Let's save metadata about mapping? 
                # Or just use filename as name.
                with open(os.path.join(recipes_dir, fname), 'w') as f:
                    f.write(r.content)
            
            # Export Assets
            assets = session.exec(select(Asset).where(Asset.project_id == proj.id)).all()
            for a in assets:
                 with open(os.path.join(assets_dir, a.name), 'wb') as f:
                     f.write(a.content)
                     
            # Create Tarball
            with tarfile.open(output_path, "w:gz") as tar:
                tar.add(tmpdir, arcname=os.path.basename(project_name))

def import_project_from_dir(root_dir: str, overwrite: bool = False):
    """
    Import a project from a directory structure.
    """
    project_json_path = os.path.join(root_dir, "project.json")
    if not os.path.exists(project_json_path):
        raise ValueError(f"Invalid project directory: 'project.json' not found in {root_dir}")

    with open(project_json_path, 'r') as f:
        meta = json.load(f)
        
    project_name = meta['name']
    
    with get_session() as session:
        # Check project existence
        existing = session.exec(select(Project).where(Project.name == project_name)).first()
        if existing:
            if not overwrite:
                raise FileExistsError(f"Project '{project_name}' already exists.")
        else:
            existing = Project(name=project_name)
            session.add(existing)
            session.commit()
            # Reload to get ID
            existing = session.exec(select(Project).where(Project.name == project_name)).first()
            
        project_id = existing.id
        
        # Import Templates
        tmpl_dir = os.path.join(root_dir, "templates")
        if os.path.exists(tmpl_dir):
            for fname in os.listdir(tmpl_dir):
                fpath = os.path.join(tmpl_dir, fname)
                if os.path.isdir(fpath): continue
                with open(fpath, 'r') as f:
                    content = f.read()
                
                # Strip .j2 for name if present
                tmpl_name = fname[:-3] if fname.endswith(".j2") else fname
                
                # Update or Create
                t = session.exec(select(Template).where(Template.name == tmpl_name).where(Template.project_id == project_id)).first()
                if t:
                    if overwrite:
                        t.content = content
                        session.add(t)
                else:
                    t = Template(name=tmpl_name, content=content, project_id=project_id)
                    session.add(t)
                    
        # Import Recipes
        recipes_dir = os.path.join(root_dir, "recipes")
        if os.path.exists(recipes_dir):
            for fname in os.listdir(recipes_dir):
                fpath = os.path.join(recipes_dir, fname)
                if os.path.isdir(fpath): continue
                with open(fpath, 'r') as f:
                    content = f.read()
                
                # Strip .lua for name if we added it
                rec_name = fname[:-4] if fname.endswith(".lua") else fname
                
                r = session.exec(select(Recipe).where(Recipe.name == rec_name).where(Recipe.project_id == project_id)).first()
                if r:
                    if overwrite:
                        r.content = content
                        session.add(r)
                else:
                    r = Recipe(name=rec_name, content=content, project_id=project_id)
                    session.add(r)
                    
        # Import Assets
        assets_dir = os.path.join(root_dir, "assets")
        if os.path.exists(assets_dir):
            for fname in os.listdir(assets_dir):
                fpath = os.path.join(assets_dir, fname)
                if os.path.isdir(fpath): continue
                with open(fpath, 'rb') as f:
                     content = f.read()
                
                a = session.exec(select(Asset).where(Asset.name == fname).where(Asset.project_id == project_id)).first()
                if a:
                    if overwrite:
                        a.content = content
                        session.add(a)
                else:
                    # source_path is lost in bundle, set to "imported"
                    a = Asset(name=fname, source_path="imported", content=content, project_id=project_id)
                    session.add(a)
                    
        session.commit()

def extract_bundle(bundle_path: str, overwrite: bool = False):
    """
    Import a project from a .project tarball.
    """
    if not os.path.exists(bundle_path):
        raise FileNotFoundError(f"Bundle '{bundle_path}' not found.")
        
    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(bundle_path, "r:gz") as tar:
            tar.extractall(path=tmpdir)
            
        # Find root folder (likely named after project)
        # We need to find 'project.json'
        # Since we tarred 'tmpdir' as arcname=project_name, it's inside a folder.
        root_dir = None
        for item in os.listdir(tmpdir):
            if os.path.isdir(os.path.join(tmpdir, item)):
                if os.path.exists(os.path.join(tmpdir, item, "project.json")):
                    root_dir = os.path.join(tmpdir, item)
                    break
        
        if not root_dir:
             # Try root of tmpdir
             if os.path.exists(os.path.join(tmpdir, "project.json")):
                 root_dir = tmpdir
             else:
                 raise ValueError("Invalid bundle: project.json not found.")
                 
        import_project_from_dir(root_dir, overwrite)

def expand_bundle_to_path(bundle_path: str, extract_path: str, overwrite: bool = False):
    """
    Extract a .project tarball to a specified path.
    """
    if not os.path.exists(bundle_path):
        raise FileNotFoundError(f"Bundle '{bundle_path}' not found.")
        
    if not os.path.exists(extract_path):
        os.makedirs(extract_path)
        
    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(bundle_path, "r:gz") as tar:
            tar.extractall(path=tmpdir)
            
        # Find root folder (likely named after project)
        root_dir = None
        for item in os.listdir(tmpdir):
            if os.path.isdir(os.path.join(tmpdir, item)):
                if os.path.exists(os.path.join(tmpdir, item, "project.json")):
                    root_dir = os.path.join(tmpdir, item)
                    break
        
        if not root_dir:
             if os.path.exists(os.path.join(tmpdir, "project.json")):
                 root_dir = tmpdir
             else:
                 raise ValueError("Invalid bundle: project.json not found.")
                 
        # Copy contents to extract_path
        for item in os.listdir(root_dir):
            s = os.path.join(root_dir, item)
            d = os.path.join(extract_path, item)
            if os.path.exists(d):
                if not overwrite:
                    raise FileExistsError(f"File '{d}' already exists. Use --overwrite to replace.")
                if os.path.isdir(d):
                    shutil.rmtree(d)
                else:
                    os.remove(d)
            
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)

def bundle_path_to_archive(source_path: str, output_path: str, overwrite: bool = False):
    """
    Create a .project tarball from a directory.
    Ignores .git, README.md, .gitignore at the root.
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source path '{source_path}' not found.")
        
    if not os.path.exists(os.path.join(source_path, "project.json")):
        raise ValueError(f"Source path '{source_path}' does not contain 'project.json'. Not a project.")
        
    if os.path.exists(output_path) and not overwrite:
        raise FileExistsError(f"Output file '{output_path}' exists. Use --overwrite to replace.")
        
    ignore_list = {".git", "README.md", ".gitignore"}
    
    # We want the archive to have a root folder named after the project
    with open(os.path.join(source_path, "project.json"), 'r') as f:
        meta = json.load(f)
    project_name = meta.get("name", os.path.basename(os.path.abspath(source_path)))
    
    with tarfile.open(output_path, "w:gz") as tar:
        for item in os.listdir(source_path):
            if item in ignore_list:
                continue
            
            s = os.path.join(source_path, item)
            # We want to add it under a folder named project_name
            tar.add(s, arcname=os.path.join(project_name, item))

def init_bundle_structure(target_path: str):
    """
    Initialize a project structure with example files.
    """
    if not os.path.exists(target_path):
        os.makedirs(target_path)
        
    project_name = os.path.basename(os.path.abspath(target_path))
    if not project_name:
        project_name = "new_project"
        
    # project.json
    proj_json_path = os.path.join(target_path, "project.json")
    if not os.path.exists(proj_json_path):
        with open(proj_json_path, 'w') as f:
            json.dump({"name": project_name, "version": "0.1.0"}, f, indent=4)
            
    # Folders
    for folder in ["templates", "recipes", "assets"]:
        os.makedirs(os.path.join(target_path, folder), exist_ok=True)
        
    # Example template
    example_tmpl = os.path.join(target_path, "templates", "example.j2")
    if not os.path.exists(example_tmpl):
        with open(example_tmpl, 'w') as f:
            f.write("Hello {{ name }}!\n")
            
    # Example recipe
    example_recipe = os.path.join(target_path, "recipes", "bundle_example.lua")
    if not os.path.exists(example_recipe):
        with open(example_recipe, 'w') as f:
            f.write('-- Example recipe\nprint("Initializing bundle project...")\n')
            
    # Example asset
    example_asset = os.path.join(target_path, "assets", "README.txt")
    if not os.path.exists(example_asset):
        with open(example_asset, 'w') as f:
            f.write("This is an example asset for your bundle project.\n")

def import_project_from_git(uri: str, overwrite: bool = False):
    """
    Import a project from a Git repository.
    Clones the repo to a temporary directory, checks for a .project file,
    and imports accordingly.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Clone the repository
        try:
            subprocess.run(["git", "clone", uri, "."], cwd=tmpdir, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to clone repository: {e.stderr}")

        # Search for .project file in the root
        project_bundles = glob.glob(os.path.join(tmpdir, "*.project"))
        
        if project_bundles:
            # If multiple bundles, just take the first one or logic it? 
            # Prompt says "If the repo contains a .project file in the root, the project should be imported from that archive."
            extract_bundle(project_bundles[0], overwrite)
        else:
            # Check for regular project structure (project.json)
            if os.path.exists(os.path.join(tmpdir, "project.json")):
                import_project_from_dir(tmpdir, overwrite)
            else:
                # If neither, maybe it's just a folder that needs to be imported as is?
                # The prompt says: "If no .project archive is present, then the bundler should attempt to import the project as if it was from a folder."
                # import_project_from_dir raises ValueError if project.json is missing.
                # If the user wants to import from a folder, they probably expect project.json to be there.
                import_project_from_dir(tmpdir, overwrite)
