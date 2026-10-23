"""Export project-owned visual references; leave source assets unchanged."""
def main():
    import json
    from pathlib import Path
    import unreal
    root=Path(unreal.Paths.project_dir()).resolve()
    out=root/'SourceArt/TerrainSurfaces/References'
    out.mkdir(parents=True,exist_ok=True)
    sources={
      'DungeonFloor':'/Game/Assets/Dungeon/Materials/Tileset1x1/Tileset1x1_1/Tileset1x1_low_DefaultMaterial_BaseColor',
      'DungeonFloorVariant':'/Game/Assets/Dungeon/Materials/Tileset1x1/Tilese1x1_2/Tileset1x1_low_DefaultMaterial_BaseColor',
      'DungeonStone':'/Game/Assets/Dungeon/Materials/Tileset1/Tileset1_low_DefaultMaterial_BaseColor',
      'FireCellNoise':'/Game/Assets/Effects/Projectiles/FireBolt/Materials/Textures/Noise_cell_1',
      'SoftNoise':'/Game/Assets/Effects/Projectiles/FireBolt/Materials/Textures/Noise_blur_1'}
    result=[]
    for name,path in sources.items():
        texture=unreal.load_asset(path)
        assert isinstance(texture,unreal.Texture2D),path
        task=unreal.AssetExportTask()
        task.object=texture
        task.filename=str(out/(name+'.png'))
        task.automated=True
        task.prompt=False
        task.replace_identical=True
        task.exporter=unreal.TextureExporterPNG()
        assert unreal.Exporter.run_asset_export_task(task),path
        result.append({'name':name,'asset':path,'export':task.filename,'width':texture.blueprint_get_size_x(),'height':texture.blueprint_get_size_y()})
    (out/'sources.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    unreal.log('SURFACE_REFERENCES '+json.dumps(result))
main()
