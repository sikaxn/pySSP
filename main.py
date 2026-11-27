if __name__ == "__main__":
    from multiprocessing import freeze_support

    freeze_support()
    from pyssp.app import main

    raise SystemExit(main())
