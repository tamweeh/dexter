if __name__ == "__main__":
    import uvicorn
    uvicorn.run("stream.columns_api:app", host="0.0.0.0", port=5000, reload=True)