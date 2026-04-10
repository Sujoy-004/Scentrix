import pinecone
print(f"Type: {type(pinecone)}")
print(f"File: {getattr(pinecone, '__file__', 'None')}")
print(f"Dir: {dir(pinecone)}")
try:
    from pinecone import Pinecone
    print("Successfully imported Pinecone class")
except ImportError as e:
    print(f"ImportError: {e}")
