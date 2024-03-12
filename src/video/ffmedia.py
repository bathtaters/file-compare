from pathlib import Path
from subprocess import run
from json import loads, dumps
    

class FFMedia:
    """Analyzer for media file"""
    
    # Command to get media info
    __cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '$FILE', # Replace with filename
        '-show_format',
        '-show_streams'
    ]

    class FFStream:
        """Single stream within a media file"""
        
        def __init__(self, stream_data: dict) -> None:
            self.data = stream_data
        
        @property
        def type(self):
            return self.data.get("codec_type")
        
        @property
        def codec(self):
            return self.data.get("codec_name")
        
        @property
        def duration(self):
            return float(self.data.get("duration"))
        
        @property
        def width(self):
            return int(self.data.get("width"))
        
        @property
        def height(self):
            return int(self.data.get("height"))
        
        @property
        def fields(self):
            return self.data.get("field_order")
        
        @property
        def fps(self):
            fps = self.data.get("r_frame_rate", "0/0/0").split("/")
            if len(fps) == 1: return float(fps[0])
            if len(fps) == 2: return float(fps[0]) / float(fps[1])
            return None
        
        def __str__(self) -> str:
            if self.type.lower() == 'video':
                return f"{self.type.capitalize()} <{self.codec}>: {round(self.duration,2)}s @ {round(self.fps,2)}fps, {self.width}x{self.height}{self.fields[:1]}"
            return f"{self.type.capitalize()} <{self.codec}>: {round(self.duration,2)}s"


    def __init__(self, filepath: str | Path) -> None:
        self.file = Path(filepath)
        raw = self.run(self.file)
        self.data = raw.get("format", {})
        self.streams = [self.FFStream(s) for s in raw.get("streams", {})]
    
    @property
    def container(self):
        return self.data.get("format_long_name")

    @property
    def duration(self):
        return float(self.data.get("duration"))
    
    def __str__(self) -> str:
        string = f"{self.file.name} <{self.container}>: {round(self.duration,2)}s"
        for stream in self.streams:
            string += f"\n  - {stream}"
        return string
    
    def __repr__(self) -> str:
        data = {
            "format": self.data,
            "streams": [repr(s) for s in self.streams],
        }
        return dumps(data, indent=2)
    
    @classmethod
    def run(cls, filepath: str | Path) -> dict:
        """Runs FFProbe command and returns resulting dictionary, or raise TypeError if no data"""
        cmd = [(str(filepath) if c == '$FILE' else c) for c in cls.__cmd]
        res = run(cmd, capture_output=True)
        if not res.stdout:
            raise TypeError(f"ERROR, Not readable by FFProbe: {filepath}")
        return loads(res.stdout)


### --- TEST --- ###
if __name__ == "__main__":
    print(FFMedia('/Users/nick/Desktop/download/A36D5C25-C302-4FBB-AE0D-91F4E0CD1DDD.mp4'))
    print(FFMedia('/Users/nick/Desktop/download/A36D5C25-C302-4FBB-AE0D-91F4E0CD1DDD_1.mp4'))